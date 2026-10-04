"""scripts/smoke.sh against the local build, served by a stub that answers like a fresh
Pages deployment: / is ready before the other paths are, and a path not published yet may
answer with the catalog's index.html, as Pages does for any path it has no file for."""

import functools
import http.server
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest
from conftest import sale_is_over
from pages_stub import AppliesHeadersFile, MissingPath

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
pytestmark = pytest.mark.skipif(not (PUBLIC / "index.html").exists(), reason="site not built")


class FreshDeployment(AppliesHeadersFile, MissingPath, http.server.SimpleHTTPRequestHandler):
    # What the build asked Pages to add: the stub serves the file the build wrote, so the smoke
    # is run against the real headers, not a copy of them.
    headers_file = (PUBLIC / "_headers").read_text(encoding="utf-8") if PUBLIC.exists() else ""
    drop = ()  # header names the deployment fails to send
    extra = {}  # header name -> value it sends in addition (Pages' own defaults)

    not_ready = {"/es/": 2}  # 404s each path gives before it is ready
    seller_status = 503
    seller_body = b"Seller access is not configured"
    fallback = {}  # times each path answers with index.html (200) before its own file
    bare_404s = 0  # 404s answered with the server's own body before the not-found page
    stale_home = 0  # times / answers with an og:image the deployment no longer has
    stale_page = 0  # GETs of / answered with the previous deployment's page (other inline script)

    def send_error(self, code, message=None, explain=None):
        if code == 404 and FreshDeployment.bare_404s > 0:
            FreshDeployment.bare_404s -= 1
            return http.server.SimpleHTTPRequestHandler.send_error(self, code, message, explain)
        return super().send_error(code, message, explain)

    def added_headers(self):
        sent = {
            name: value
            for name, value in super().added_headers().items()
            if name.lower() not in {d.lower() for d in self.drop}
        }
        return {**sent, **self.extra}

    def do_GET(self):
        if self.path == "/" and FreshDeployment.stale_page > 0:
            # The alias has moved and the edge mixes two deployments: the previous page, whose
            # inline script hashes differently, under this deployment's policy.
            FreshDeployment.stale_page -= 1
            body = re.sub(
                r"<script>",
                "<script>// previous deployment\n",
                (Path(self.directory) / "index.html").read_text(encoding="utf-8"),
                count=1,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.not_ready.get(self.path, 0) > 0:
            self.not_ready[self.path] -= 1
            self.send_error(404)
            return
        if self.path.split("?")[0].startswith("/seller"):
            # Cloudflare Access answers an anonymous visitor before the page; the middleware
            # without its configuration answers 503. Either way, no page body.
            self.send_response(self.seller_status)
            self.send_header("Content-Length", str(len(self.seller_body)))
            self.end_headers()
            self.wfile.write(self.seller_body)
            return
        if self.path == "/" and FreshDeployment.stale_home > 0:
            # The previous deployment's page, naming a cover photo this one has deleted.
            FreshDeployment.stale_home -= 1
            body = re.sub(
                r'(<meta property="og:image" content="https://[^/]+/)[^"]+',
                r"\1catalog/deleted-cover.jpg",
                (Path(self.directory) / "index.html").read_text(encoding="utf-8"),
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.fallback.get(self.path, 0) > 0:
            self.fallback[self.path] -= 1
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *args):
        pass


def smoke(
    retries,
    seller=(503, b"Seller access is not configured"),
    not_ready=None,
    fallback=None,
    bare_404s=0,
    stale_home=0,
    stale_page=0,
    drop=(),
    extra=None,
):
    FreshDeployment.drop, FreshDeployment.extra = drop, extra or {}
    FreshDeployment.not_ready = {"/es/": 2} if not_ready is None else not_ready
    FreshDeployment.fallback = fallback or {}
    FreshDeployment.bare_404s = bare_404s
    FreshDeployment.stale_home = stale_home
    FreshDeployment.stale_page = stale_page
    FreshDeployment.seller_status, FreshDeployment.seller_body = seller
    handler = functools.partial(FreshDeployment, directory=str(PUBLIC))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            return subprocess.run(
                ["bash", "scripts/smoke.sh", f"http://127.0.0.1:{server.server_port}"],
                cwd=ROOT,
                env={**os.environ, "SMOKE_RETRIES": str(retries), "SMOKE_RETRY_DELAY": "1"},
                capture_output=True,
                text=True,
                timeout=120,
            )
        finally:
            server.shutdown()


def test_a_path_that_is_not_ready_yet_is_retried():
    result = smoke(retries=3)
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


def test_without_retries_the_same_deployment_fails():
    # Proves the stub reproduces the CI failure, so the test above exercises the retry.
    result = smoke(retries=0)
    assert result.returncode != 0
    assert "404" in result.stderr


@pytest.mark.parametrize(
    "body",
    [
        b'<script type="application/json" id="sealed">{"v":1}</script>',
        b'{"v":1,"kdf":"PBKDF2-SHA256","iter":1000000}',
    ],
)
def test_an_anonymous_seller_page_carrying_the_envelope_fails_the_smoke(body):
    """In catalog mode the envelope check refuses it; with the sale over, the end smoke refuses
    any page at all there. Either way a deployment serving the envelope anonymously fails."""
    result = smoke(retries=3, seller=(200, body))
    assert result.returncode != 0
    if sale_is_over():
        assert "/seller/ answers 200 on the end page" in result.stderr
    else:
        assert "/seller/ serves the sealed envelope anonymously" in result.stderr


def test_a_redirect_in_front_of_the_seller_page_passes_the_smoke():
    result = smoke(retries=3, seller=(302, b""))
    assert result.returncode == 0, result.stderr


def test_an_unknown_path_that_answers_200_fails(monkeypatch):
    # Pages with no 404.html: every unknown path is the catalog and a 200.
    monkeypatch.setattr(FreshDeployment, "spa_fallback", True)
    result = smoke(retries=3)
    assert result.returncode != 0
    assert "answers 200, not 404" in result.stderr


def test_a_404_that_is_not_the_not_found_page_fails(monkeypatch):
    monkeypatch.setattr(FreshDeployment, "not_found_page", "no-such-page.html")
    result = smoke(retries=3)
    assert result.returncode != 0
    assert "the 404 is not the not-found page" in result.stderr


def test_a_404_with_another_body_first_is_retried():
    # CI run 37169206079 (#173): a fresh deployment answered 404 with its own body, a second
    # after / was 200, and smoke failed on the first reply instead of asking again.
    result = smoke(retries=3, not_ready={}, bare_404s=2)
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


def test_a_page_still_naming_a_deleted_cover_is_fetched_again():
    # #166: the deploy that replaced the cover failed on the old page's og:image, which the new
    # deployment had deleted. The page is fetched again, so the image checked is the current one.
    result = smoke(retries=3, not_ready={}, stale_home=2)
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


def test_a_cover_that_stays_missing_fails():
    result = smoke(retries=1, not_ready={}, stale_home=9)
    assert result.returncode != 0
    assert "catalog og:image" in result.stderr


def test_robots_txt_served_as_the_catalog_is_retried():
    result = smoke(retries=3, not_ready={}, fallback={"/robots.txt": 2})
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


def test_robots_txt_that_stays_the_catalog_fails_as_such():
    # Without the retry this read as "robots.txt is permissive", which blamed the file.
    result = smoke(retries=1, not_ready={}, fallback={"/robots.txt": 5})
    assert result.returncode != 0
    assert "robots.txt is served as a page" in result.stderr


# The security headers (ADR-010): the first deployment that stops sending one fails here, not
# in a buyer's browser.


@pytest.mark.parametrize(
    "header", ["Strict-Transport-Security", "Content-Security-Policy", "Permissions-Policy"]
)
def test_a_deployment_that_stops_sending_a_security_header_fails(header):
    result = smoke(retries=3, not_ready={}, drop=[header])
    assert result.returncode != 0
    assert f"{header} is not served" in result.stderr


def test_a_policy_that_does_not_list_the_pages_inline_script_fails():
    """The page is what the build wrote, the policy a copy of its hashes: if the edge rewrites
    the page, the hash no longer matches and the browser would run nothing."""
    policy = FreshDeployment.headers_file
    stale = re.sub(r"'sha256-[^']+'", "'sha256-AAAA'", policy)
    result = smoke(
        retries=3,
        not_ready={},
        drop=["Content-Security-Policy"],
        extra={
            "Content-Security-Policy": re.search(r"Content-Security-Policy: (.*)", stale).group(1)
        },
    )
    assert result.returncode != 0
    assert "does not list an inline script" in result.stderr


def test_a_page_from_the_previous_deployment_is_fetched_again():
    """Production run 37176954819: right after the alias moved, / came back with an inline
    script its policy did not list, and minutes later the same URL passed. The page and its
    policy come from one response, and a mismatch is read again."""
    result = smoke(retries=6, not_ready={}, stale_page=6)
    assert result.returncode == 0, result.stderr


def test_a_mixed_policy_without_retries_fails():
    result = smoke(retries=0, not_ready={}, stale_page=6)
    assert result.returncode != 0
    assert "does not list an inline script" in result.stderr


def test_pages_wildcard_cors_header_is_a_warning_not_a_failure():
    """The `! Access-Control-Allow-Origin` detach is Cloudflare's to honour and no test here can
    see it, so a deployment that still sends the header is reported and still ships."""
    result = smoke(retries=3, not_ready={}, extra={"Access-Control-Allow-Origin": "*"})
    assert result.returncode == 0, result.stderr
    assert "SMOKE WARN" in result.stderr
