"""
/seller/* has its own Content-Security-Policy (ADR-007 decision 5; FEAT-009 PR 2, AC9): scripts
from 'self' only, no network, no framing. It is set by functions/_middleware.js, which already
handles that path, so it is on the response the browser gets whatever _headers does with a
response that passed through a Function.

What counts is the served header, which no test here can see in production: the owner checks it
after an Access login (docs/runbooks/ops.md). What these tests prove is the mechanism, and that
the page runs under exactly the policy the middleware sends.
"""

import functools
import http.server
import json
import re
import threading
from pathlib import Path

import pytest
from browser_harness import needs_chrome, run_page
from sealed_helpers import PASSPHRASE, build_site, node, seal_fixture

from leaving_denver import site_builder

# A response through the middleware for each path, as {status, csp, body, ...}.
JWT_FLOW = """
import { onRequest } from './functions/_middleware.js';
const domain = 'https://example.cloudflareaccess.com';
const aud = 'a'.repeat(64);
const pair = await crypto.subtle.generateKey({
  name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048,
  publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256'
}, true, ['sign', 'verify']);
const jwk = { ...await crypto.subtle.exportKey('jwk', pair.publicKey), kid: 'test-key', alg: 'RS256' };
globalThis.fetch = async () => Response.json({ keys: [jwk] });
const encode = data => Buffer.from(JSON.stringify(data)).toString('base64url');
async function signed(payload) {
  const body = `${encode({ kid: 'test-key', alg: 'RS256' })}.${encode(payload)}`;
  const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', pair.privateKey, new TextEncoder().encode(body));
  return `${body}.${Buffer.from(signature).toString('base64url')}`;
}
const valid = { iss: domain, aud: [aud], exp: Math.floor(Date.now() / 1000) + 3600 };
const out = {};
async function through(path, env, headers, next) {
  const response = await onRequest({
    env, request: new Request(`https://leaving-denver.pages.dev${path}`, { headers }),
    functionPath: '/', data: {}, waitUntil() {}, passThroughOnException() {}, next,
  });
  return { status: response.status, csp: response.headers.get('Content-Security-Policy'),
    body: await response.text(), type: response.headers.get('Content-Type'),
    kept: response.headers.get('X-Kept') };
}
const configured = { ACCESS_TEAM_DOMAIN: domain, ACCESS_AUD: aud };
const token = { 'Cf-Access-Jwt-Assertion': await signed(valid) };
const page = () => new Response('seller page', { headers: { 'Content-Type': 'text/html', 'X-Kept': 'yes' } });
out.seller = await through('/seller/', configured, token, page);
out.module = await through('/seller/seller.mjs', configured, token, page);
out.encoded = await through('/%73eller/', configured, token, page);
out.unconfigured = await through('/seller/', {}, {}, page);
out.noToken = await through('/seller/', configured, {}, page);
out.notModified = await through('/seller/', configured, token, () => new Response(null, { status: 304 }));
out.immutable = await through('/seller/', configured, token, () => Response.redirect('https://example.com/', 302));
out.catalog = await through('/', {}, {}, page);
out.share = await through('/i/sofa-sleeper/', {}, {}, page);
out.nearMiss = await through('/sellers/', {}, {}, page);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def served():
    result = node(JWT_FLOW)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def directives(policy):
    parsed = {}
    for part in filter(str.strip, policy.split(";")):
        name, *sources = part.split()
        parsed[name.lower()] = sources
    return parsed


def test_the_seller_page_is_served_with_the_policy_and_keeps_its_own_headers(served):
    page = served["seller"]
    assert page["status"] == 200
    assert page["body"] == "seller page"
    assert page["kept"] == "yes", "the response keeps the headers it came with"
    assert page["type"] == "text/html"
    rules = directives(page["csp"])
    assert rules["script-src"] == ["'self'"]
    assert rules["connect-src"] == ["'none'"]
    assert rules["frame-ancestors"] == ["'none'"]


def test_the_policy_allows_nothing_unsafe_or_remote(served):
    policy = served["seller"]["csp"]
    for unsafe in ("unsafe-inline", "unsafe-eval", "http:", "https:", "data:", "blob:", "*"):
        assert unsafe not in policy.split(), unsafe
    for sources in directives(policy).values():
        assert not any(re.match(r"^https?://", source) for source in sources), sources
    assert directives(policy)["default-src"] == ["'none'"]


def test_every_response_under_seller_carries_it_and_nothing_else_does(served):
    policy = served["seller"]["csp"]
    assert policy, "the seller page has a policy"
    for name in (
        "seller",
        "module",
        "encoded",
        "unconfigured",
        "noToken",
        "notModified",
        "immutable",
    ):
        assert served[name]["csp"] == policy, name
    for name in ("catalog", "share", "nearMiss"):
        assert served[name]["csp"] is None, f"{name} must not get a policy (ADR-005 beacon)"


def test_a_response_with_no_body_or_immutable_headers_still_gets_the_policy(served):
    assert served["notModified"]["status"] == 304
    assert served["immutable"]["status"] == 302


def test_the_seller_policy_is_in_the_middleware_not_in_the_static_headers(served):
    """The static headers carry the public policy (ADR-010) and none of the seller's: a response
    through the middleware must never hold two policies, which a browser enforces together."""
    from leaving_denver.site_builder import pages_headers

    static = pages_headers(["'sha256-x'"])
    assert served["seller"]["csp"] not in static
    assert "connect-src 'none'" not in static


# The page runs under exactly this policy


class PolicyHandler(http.server.SimpleHTTPRequestHandler):
    policy = ""

    def end_headers(self):
        self.send_header("Content-Security-Policy", self.policy)
        super().end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def served_page(tmp_path, served):
    dist = tmp_path / "public"
    patcher = pytest.MonkeyPatch()
    try:
        build_site(dist, patcher, sealed=seal_fixture())
        site_builder.build_stylesheets()
    finally:
        patcher.undo()
    handler = type("Handler", (PolicyHandler,), {"policy": served["seller"]["csp"]})
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(handler, directory=str(dist))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/seller/"
    server.shutdown()


@needs_chrome
def test_the_page_unlocks_under_its_own_policy_with_no_violation(tmp_path, served_page):
    """The policy forbids inline scripts and styles: a page that still used one would stay
    dead here while every file:// test passed (file:// carries no header)."""
    result = run_page(
        tmp_path,
        None,
        f"""
const $ = id => document.getElementById(id);
$('passphrase').value = {json.dumps(PASSPHRASE)};
$('unlock').requestSubmit();
await wait(50);
await until(() => !$('unlock-button').disabled && $('private-views').childElementCount > 0, 20000);
return {{ violations: window.VIOLATIONS, views: $('private-views').childElementCount,
  items: $('item').options.length, description: $('description').value.length }};
""",
        setup="""
window.VIOLATIONS = [];
document.addEventListener('securitypolicyviolation',
  event => window.VIOLATIONS.push(`${event.violatedDirective} ${event.blockedURI}`));
""",
        url=served_page,
    )
    assert result["violations"] == []
    assert result["items"] > 0
    assert result["description"] > 0
    assert result["views"] > 0


# What the policy forbids must not creep back in: a file:// test cannot see the header


SELLER_TEMPLATE = Path(__file__).resolve().parents[1] / "src/leaving_denver/templates/seller.html"
SELLER_SCRIPT = Path(__file__).resolve().parents[1] / "src/leaving_denver/assets/seller.mjs"


def test_the_seller_template_has_no_inline_code_or_style():
    html = SELLER_TEMPLATE.read_text(encoding="utf-8")
    for tag in re.findall(r"<script\b[^>]*>", html):
        assert 'type="application/json"' in tag or 'type="module"' in tag, tag
    assert not re.search(r"<script\b[^>]*type=\"module\"(?![^>]*\bsrc=)", html)
    assert "<style" not in html
    assert not re.search(r"\sstyle\s*=", html)
    assert not re.search(r"\son[a-z]+\s*=", html), "an inline event handler"


# Each is a way the page could reach the network, keep something, or run text as code.
FORBIDDEN_IN_THE_PAGE_SCRIPT = [
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "importScripts",
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "document.cookie",
    "caches.",
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "eval(",
    "new Function",
    "setAttribute('style'",
    'setAttribute("style"',
    "import(",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_IN_THE_PAGE_SCRIPT)
def test_the_page_script_uses_no_network_storage_or_dynamic_code(forbidden):
    assert forbidden not in SELLER_SCRIPT.read_text(encoding="utf-8")
