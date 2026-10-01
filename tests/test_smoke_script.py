"""scripts/smoke.sh against the local build, served by a stub that answers like a fresh
Pages deployment: / is ready before the other paths are, and a path not published yet may
answer with the catalog's index.html, as Pages does for any path it has no file for."""

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
    fallback = {}  # times each path answers with index.html (200) before its own file

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self):
        if self.not_ready.get(self.path, 0) > 0:
            self.not_ready[self.path] -= 1
            self.send_error(404)
            return
        if self.fallback.get(self.path, 0) > 0:
            self.fallback[self.path] -= 1
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *args):
        pass


def smoke(retries, not_ready=None, fallback=None):
    FreshDeployment.not_ready = {"/es/": 2} if not_ready is None else not_ready
    FreshDeployment.fallback = fallback or {}
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


def test_robots_txt_served_as_the_catalog_is_retried():
    result = smoke(retries=3, not_ready={}, fallback={"/robots.txt": 2})
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


def test_robots_txt_that_stays_the_catalog_fails_as_such():
    # Without the retry this read as "robots.txt is permissive", which blamed the file.
    result = smoke(retries=1, not_ready={}, fallback={"/robots.txt": 5})
    assert result.returncode != 0
    assert "robots.txt is served as a page" in result.stderr
