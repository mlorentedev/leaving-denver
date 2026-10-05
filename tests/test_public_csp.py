"""
The public pages' security headers and Content-Security-Policy (ADR-010; /seller/* keeps its own,
ADR-007).

What counts is what a browser does with the response, so the headline tests serve the built
site over HTTP with the headers its own `_headers` file asks Pages to add (a `file://` page
carries none, lesson-024) and drive the pages in headless Chrome: any blocked script, style or
request, and any console error, fails them. The static tests pin what a browser cannot show: the
policy lists exactly the inline scripts the build emitted, and the page templates carry no inline
style or handler that the policy would have to allow.
"""

import base64
import functools
import hashlib
import http.server
import re
import threading
from pathlib import Path

import pytest
from browser_harness import PUBLIC, needs_chrome, open_page, page_items, pointer
from pages_stub import AppliesHeadersFile, MissingPath, pages_headers_for, policy_directives

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]
# An inline style or event handler is an attribute, so it only exists inside a tag. Anchoring
# there (BUG-017) keeps the page script's own JS from failing the guard: `const style = …`,
# `box.style.width = …` and `const online = …` are not markup, and `style-src 'self'` does not
# govern them anyway. `[^>]*` crosses newlines, so a wrapped attribute still matches.
STYLE_ATTR = re.compile(r"<[a-zA-Z][^>]*\sstyle\s*=")
HANDLER_ATTR = re.compile(r"<[a-zA-Z][^>]*\son[a-z]+\s*=")
CAR = "2019-ford-escape-sel-awd"
BEACON_SCRIPT = "https://static.cloudflareinsights.com"
BEACON_CONNECT = "https://cloudflareinsights.com"
# What the policy must leave on for the pages' own origin (ADR-010): every "copy" button, and
# the share button (web-share), which is left unnamed because Chrome logs an error for a feature
# it does not know on its platform and desktop Linux, where Lighthouse runs, lacks it.
KEPT_FEATURES = ("clipboard-write",)
DENIED_FEATURES = (
    "accelerometer",
    "autoplay",
    "browsing-topics",
    "camera",
    "display-capture",
    "geolocation",
    "gyroscope",
    "hid",
    "idle-detection",
    "magnetometer",
    "microphone",
    "midi",
    "payment",
    "publickey-credentials-get",
    "screen-wake-lock",
    "serial",
    "usb",
    "xr-spatial-tracking",
)
# The script an API needs, by the feature that governs it: a page that starts using one of
# these while its feature is denied would break on a phone and in no test.
API_OF_FEATURE = {
    "camera": r"getUserMedia|mediaDevices",
    "microphone": r"getUserMedia|mediaDevices",
    "geolocation": r"geolocation",
    "payment": r"PaymentRequest",
    "usb": r"navigator\.usb",
    "serial": r"navigator\.serial",
    "hid": r"navigator\.hid",
    "midi": r"requestMIDIAccess",
    "screen-wake-lock": r"wakeLock",
    "display-capture": r"getDisplayMedia",
    "idle-detection": r"IdleDetector",
    "publickey-credentials-get": r"navigator\.credentials",
}


def end_inventory():
    data = site_builder.load_inventory_yaml()
    data["seller"]["sale_over"] = True
    return data


@pytest.fixture(scope="module")
def end_site(tmp_path_factory):
    """The end-of-sale build (OPS-011), made in a directory of its own."""
    dist = tmp_path_factory.mktemp("end") / "public"
    patcher = pytest.MonkeyPatch()
    try:
        patcher.setattr(site_builder, "DIST_DIR", dist)
        patcher.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
        patcher.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
        patcher.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
        site_builder.build_stylesheets()
        site_builder.build_public_site(end_inventory())
    finally:
        patcher.undo()
    return dist


@pytest.fixture(params=["built", "end"])
def site(request, end_site):
    """What `make build` made (the catalog, or the end page if the switch is on) and the end
    build, whichever mode the repository is in."""
    return PUBLIC if request.param == "built" else end_site


def served_headers(root):
    return (root / "_headers").read_text(encoding="utf-8")


def public_pages(root):
    return [p for p in sorted(root.rglob("*.html")) if "seller" not in p.relative_to(root).parts]


def inline_scripts(html):
    """The bodies of the scripts a browser would run from the page itself."""
    found = []
    for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script>", html, re.S):
        if "src=" not in attrs and not re.search(r'type="(?!module")', attrs):
            found.append(body)
    return found


def hash_of(script):
    digest = hashlib.sha256(script.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode() + "'"


def policy_at(root, path="/"):
    headers = pages_headers_for(served_headers(root), path)
    assert "Content-Security-Policy" in headers, f"no policy at {path}"
    return headers["Content-Security-Policy"]


# The header values


def test_every_path_gets_the_transport_and_isolation_headers(site):
    headers = pages_headers_for(served_headers(site), "/anything/at/all")
    assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
    # Not COEP: require-corp would block the beacon and every image that sends no CORP header.
    assert "Cross-Origin-Embedder-Policy" not in headers
    # Not CORP (ADR-010): a hotlinked photo is the one thing it could break, and nothing it
    # would protect is secret.
    assert "Cross-Origin-Resource-Policy" not in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_pages_own_wildcard_cors_header_is_detached(site):
    """Pages adds `Access-Control-Allow-Origin: *` to static assets. No page here is fetched
    cross-origin, so the `_headers` file removes it (`! Name`, Pages' detach syntax)."""
    lines = [line.strip() for line in served_headers(site).splitlines()]
    assert "! Access-Control-Allow-Origin" in lines
    assert "Access-Control-Allow-Origin" not in pages_headers_for(served_headers(site), "/")


def test_the_permissions_policy_denies_the_powerful_features_and_keeps_the_pages_own(site):
    value = pages_headers_for(served_headers(site), "/")["Permissions-Policy"]
    features = dict(re.findall(r"([a-z-]+)=(\([^)]*\))", value))
    for feature in DENIED_FEATURES:
        assert features.get(feature) == "()", feature
    for feature in KEPT_FEATURES:
        assert features.get(feature) == "(self)", feature
    assert features.get("web-share") != "()", "the share button would stop working"


@pytest.mark.parametrize("feature", DENIED_FEATURES)
def test_no_page_script_uses_a_feature_the_policy_denies(feature):
    if feature not in API_OF_FEATURE:
        pytest.skip("no API of its own to look for")
    for page in public_pages(PUBLIC):
        scripts = "".join(inline_scripts(page.read_text(encoding="utf-8")))
        assert not re.search(API_OF_FEATURE[feature], scripts), f"{page.name} uses {feature}"


def test_the_page_script_uses_the_features_the_policy_keeps():
    """If the page stopped needing one, the allowance is stale; if it grows another, the policy
    must name it. Both fail here rather than on a phone."""
    scripts = "".join(
        inline_scripts((ROOT / "src/leaving_denver/templates/index.html").read_text("utf-8"))
    )
    assert "navigator.share" in scripts
    assert "navigator.clipboard" in scripts


# The Content-Security-Policy


def test_the_policy_restricts_every_source_and_allows_the_beacon(site):
    rules = policy_directives(policy_at(site))
    scripts = [s for s in rules["script-src"] if not s.startswith("'sha256-")]
    assert scripts == ["'self'", BEACON_SCRIPT]
    assert rules["connect-src"] == ["'self'", BEACON_CONNECT]
    assert rules["default-src"] == ["'none'"]
    assert rules["style-src"] == ["'self'"]
    assert rules["font-src"] == ["'self'"]
    assert rules["img-src"] == ["'self'"]
    for closed in ("frame-ancestors", "base-uri", "object-src", "form-action"):
        assert rules[closed] == ["'none'"], closed
    everything = " ".join(src for sources in rules.values() for src in sources)
    for unsafe in ("unsafe-inline", "unsafe-eval", "unsafe-hashes", "http:", "https:", "*"):
        assert unsafe not in everything.split(), unsafe


def test_the_policy_is_one_header_on_every_path_the_404_included(site):
    """Two Content-Security-Policy values are two policies and a page must pass both, so the
    one `/*` rule is the only place the header is written. A path rule alone would miss the
    404 page, which Pages serves at the URL that was asked for (lesson-026)."""
    text = served_headers(site)
    assert len(re.findall(r"^\s*Content-Security-Policy:", text, re.M)) == 1
    for path in ("/", "/es/", "/index.html", "/?utm_source=flyer", "/i/x/", "/nope/deep/er"):
        assert policy_at(site, path) == policy_at(site)


def test_the_policy_lists_exactly_the_inline_scripts_the_build_emitted(site):
    """No script runs that the build did not write, and no hash is left over from one it no
    longer writes. The hashes come from the emitted pages, never from a constant."""
    emitted = {
        hash_of(script)
        for page in public_pages(site)
        for script in inline_scripts(page.read_text(encoding="utf-8"))
    }
    listed = {s for s in policy_directives(policy_at(site))["script-src"] if "sha256-" in s}
    assert listed == emitted


def test_the_policy_is_written_after_every_page_it_covers(tmp_path):
    """`_headers` is the last file written: a page made after it would carry a script the
    policy does not list."""
    source = (ROOT / "src/leaving_denver/site_builder.py").read_text(encoding="utf-8")
    for name in ("build_public_site", "build_end_site"):
        body = source.split(f"def {name}(")[1].split("\ndef ")[0]
        assert "write_headers()" in body, name
        tail = body.split("write_headers()")[1]
        assert not re.search(r"write_text|write_not_found|write_flyer|sweep_to_end_site", tail)


def test_the_pages_carry_no_inline_style_handler_or_javascript_url(site):
    """`style-src 'self'` and no `unsafe-hashes` leave these dead: found here, not on a phone."""
    for page in public_pages(site):
        html = page.read_text(encoding="utf-8")
        where = page.relative_to(site)
        assert "<style" not in html, f"{where}: an inline <style>"
        assert not STYLE_ATTR.search(html), f"{where}: a style attribute"
        assert not HANDLER_ATTR.search(html), f"{where}: an inline event handler"
        assert "javascript:" not in html, where


def test_the_attribute_guards_ignore_a_javascript_local_named_style():
    """BUG-017: the guard wants markup, not the page script's own JS. `const style =` was a
    false positive that forced a local rename in FEAT-016 (#190); `box.style.width =` and
    `one =` are not inline style or an event handler and the policy does not govern them."""
    js = "const style = getComputedStyle(photoFrame);\nstyle = box.style.width;\nconst online = true;"
    assert not STYLE_ATTR.search(js)
    assert not HANDLER_ATTR.search(js)


def test_the_attribute_guards_still_flag_real_attributes():
    """The anchor must narrow the guard, not empty it: both real attributes stay caught,
    across newlines too."""
    html = '<div class="a"\n  style="color:red" onclick="go()">x</div>'
    assert STYLE_ATTR.search(html)
    assert HANDLER_ATTR.search(html)


def test_the_page_script_sets_no_style_attribute_or_markup():
    scripts = "".join(
        inline_scripts((ROOT / "src/leaving_denver/templates/index.html").read_text("utf-8"))
    )
    assert "setAttribute('style'" not in scripts
    assert 'setAttribute("style"' not in scripts
    assert "cssText" not in scripts
    assert "eval(" not in scripts
    assert "new Function" not in scripts


def test_the_seller_page_is_not_given_a_second_policy():
    """ADR-007: the middleware sets /seller/*'s policy on the response. The static one carries
    none of its directives, so no response can hold both, whatever Pages does with _headers."""
    text = served_headers(PUBLIC)
    assert "connect-src 'none'" not in text
    assert "seller" not in text


# The policy against a browser


class Pages(AppliesHeadersFile, MissingPath, http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def serve():
    servers = []

    def start(root):
        handler = type("Handler", (Pages,), {"headers_file": served_headers(root)})
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(handler, directory=str(root))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()


# Recorded before any page script: what the policy blocked, and what the page did with the
# share sheet and the clipboard (stubbed, since a headless Chrome has neither).
SETUP = """
window.VIOLATIONS = [];
document.addEventListener('securitypolicyviolation',
  event => window.VIOLATIONS.push(`${event.violatedDirective} ${event.blockedURI}`));
window.LOG = [];
const share = data => { window.LOG.push('share ' + data.url); return Promise.resolve(); };
Object.defineProperty(navigator, 'share', { configurable: true, value: share });
Object.defineProperty(navigator, 'clipboard', { configurable: true,
  value: { writeText: text => { window.LOG.push('copy ' + text); return Promise.resolve(); } } });
"""


def no_trouble(browser):
    """Nothing blocked, nothing logged as an error, no Permissions-Policy complaint."""
    assert browser.run("return window.VIOLATIONS;") == []
    assert browser.errors() == []
    assert [e["text"] for e in browser.logged if "Permissions-Policy" in e["text"]] == []


CATALOG_STEPS = """
const id = INVENTORY.items.find(i => i.photos.length > 2).id;
document.querySelector(`.item-card[data-item="${id}"]`).click();
await until(() => sheets().includes('itemSheet'));
const count = () => document.getElementById('modalPhotoCount').textContent;
const first = count();
document.getElementById('modalNextPhoto').click();
const arrow = count();
const photos = INVENTORY.items.find(i => i.id === id).photos.length;
return { id, first, arrow, photos, open: sheets(),
  features: ['clipboard-write', 'camera', 'geolocation', 'payment']
    .map(f => document.featurePolicy.allowsFeature(f)) };
"""


def drive_catalog(browser):
    state = browser.run(CATALOG_STEPS)
    assert state["open"] == ["itemSheet"], "the item sheet did not open"
    assert state["first"] == f"1 / {state['photos']}"
    assert state["arrow"] == f"2 / {state['photos']}", "the arrow did not step"
    # web-share is left to the header test: a desktop Chrome does not offer the feature at all.
    assert state["features"] == [True, False, False, False]
    browser.key("ArrowRight", 39)
    assert browser.run("return document.getElementById('modalPhotoCount').textContent;") == (
        f"3 / {state['photos']}"
    )
    # Share: the Web Share API where there is one, then the clipboard where there is not.
    browser.run("document.getElementById('modalShare').click(); await wait(30);")
    browser.run(
        "Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });"
        "document.getElementById('modalShare').click(); await wait(30);"
    )
    log = browser.run("return window.LOG;")
    assert [entry.split()[0] for entry in log] == ["share", "copy"]
    assert log[0].split()[1] == log[1].split()[1].strip()
    # The contact sheet, which a mouse gets in place of the sms: hand-off.
    browser.run("document.querySelector('[data-sms-intent]').click(); await wait(30);")
    assert browser.run("return sheets();") == ["itemSheet", "contactSheet"]
    browser.run("document.getElementById('contactCopy').click(); await wait(30);")
    assert browser.run("return window.LOG.length;") == 3
    browser.run("document.querySelector('#contactSheet [data-close-sheet]').click();")
    browser.run("await until(() => sheets().length === 1);")
    browser.run("document.querySelector('#itemSheet [data-close-sheet]').click();")
    browser.run("await until(() => sheets().length === 0);")
    assert browser.run("return sheets();") == []
    # The car's card opens its sheet from data-open-item (it had an inline onclick): both the
    # photo and the specs button.
    for opener in ("div[data-open-item]", "button[data-open-item]"):
        opened = browser.run(
            f"document.querySelector({opener!r}).click(); await until(() => sheets().length);"
            f"const title = document.getElementById('modalTitle').textContent;"
            f"document.querySelector('#itemSheet [data-close-sheet]').click();"
            f"await until(() => !sheets().length); return title;"
        )
        assert opened == browser.run(f"return INVENTORY.items.find(i => i.id === {CAR!r}).title;")


@needs_chrome
@pytest.mark.parametrize("page", ["/", "/es/"])
def test_the_catalog_works_under_its_policy(tmp_path, serve, page):
    base = serve(PUBLIC)
    setup = pointer(fine=True) + SETUP
    with open_page(tmp_path, None, setup=setup, url=base + page) as browser:
        drive_catalog(browser)
        no_trouble(browser)


@needs_chrome
def test_a_share_page_still_sends_the_buyer_to_the_item(tmp_path, serve):
    """The share page's redirect is an inline script: if the policy blocked it the buyer
    would stay on a link, and only a browser shows that."""
    _, _, items = page_items("index.html")
    base = serve(PUBLIC)
    url = f"{base}/i/{items[0]}/"
    with open_page(tmp_path, None, setup=SETUP, url=url) as browser:
        browser.run("await until(() => location.pathname === '/' && sheets().length);")
        assert browser.run("return [location.pathname, sheets()];") == ["/", ["itemSheet"]]
        no_trouble(browser)


@needs_chrome
@pytest.mark.parametrize("path", ["/flyer/", "/not/a/page/"])
def test_the_flyer_and_the_404_page_run_under_the_policy(tmp_path, serve, path):
    base = serve(PUBLIC)
    with open_page(tmp_path, None, setup=SETUP, url=base + path) as browser:
        styled = browser.run(
            "await wait(100); return getComputedStyle(document.body).fontFamily + '|' +"
            " (document.querySelector('.qr svg') || document.querySelector('[data-role]')).tagName;"
        )
        assert "Plus Jakarta Sans" in styled, "the page's own style did not apply"
        no_trouble(browser)


@needs_chrome
@pytest.mark.parametrize("path", ["/", "/es/", "/not/a/page/"])
def test_the_end_pages_run_under_the_policy(tmp_path, serve, end_site, path):
    base = serve(end_site)
    with open_page(tmp_path, None, setup=SETUP, url=base + path) as browser:
        styled = browser.run("await wait(100); return getComputedStyle(document.body).fontFamily;")
        assert "Plus Jakarta Sans" in styled
        no_trouble(browser)


@needs_chrome
def test_a_blocked_inline_script_is_seen_by_the_test(tmp_path, serve, end_site):
    """The test above only means something if it fails on a page the policy stops: a copy of
    the end page with an inline script of its own, which the policy does not list."""
    root = tmp_path / "site"
    root.mkdir()
    for entry in end_site.iterdir():
        if entry.name != "index.html":
            (root / entry.name).symlink_to(entry)
    page = (end_site / "index.html").read_text(encoding="utf-8")
    (root / "index.html").write_text(
        page.replace("</body>", "<script>window.RAN = true;</script></body>"), encoding="utf-8"
    )
    with open_page(tmp_path, None, setup=SETUP, url=serve(root) + "/") as browser:
        assert browser.run("return window.RAN === true;") is False
        assert browser.run("return window.VIOLATIONS.length;") == 1
        assert browser.errors(), "Chrome logged no error for the blocked script"
