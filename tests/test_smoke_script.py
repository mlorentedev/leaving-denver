"""scripts/smoke.sh against the local build, served by a stub that answers like a fresh
Pages deployment: / is ready before the other paths are."""

import functools
import http.server
import os
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
pytestmark = pytest.mark.skipif(not (PUBLIC / "index.html").exists(), reason="site not built")


class FreshDeployment(http.server.SimpleHTTPRequestHandler):
    not_ready = {"/es/": 2}  # 404s each path gives before it is ready
    seller_status = 503
    seller_body = b"Seller access is not configured"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self):
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
        super().do_GET()

    def log_message(self, *args):
        pass


def smoke(retries, seller=(503, b"Seller access is not configured")):
    FreshDeployment.not_ready = {"/es/": 2}
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
    result = smoke(retries=3, seller=(200, body))
    assert result.returncode != 0
    assert "/seller/ serves the sealed envelope anonymously" in result.stderr


def test_an_access_wall_in_front_of_the_seller_page_passes_the_smoke():
    result = smoke(retries=3, seller=(302, b""))
    assert result.returncode == 0, result.stderr
