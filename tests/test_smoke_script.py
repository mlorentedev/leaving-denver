"""scripts/smoke.sh against the local build, served by a stub that answers like a fresh
Pages deployment: / is ready before the other paths are."""

import functools
import http.server
import os
import subprocess
import threading
from pathlib import Path

import pytest
from pages_stub import MissingPath

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
pytestmark = pytest.mark.skipif(not (PUBLIC / "index.html").exists(), reason="site not built")


class FreshDeployment(MissingPath, http.server.SimpleHTTPRequestHandler):
    not_ready = {"/es/": 2}  # 404s each path gives before it is ready

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self):
        if self.not_ready.get(self.path, 0) > 0:
            self.not_ready[self.path] -= 1
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


def smoke(retries):
    FreshDeployment.not_ready = {"/es/": 2}
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
