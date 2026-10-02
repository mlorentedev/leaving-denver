"""scripts/smoke.sh against a served end-of-sale build (OPS-011).

Smoke runs against a URL, so it learns the mode from the page it is served, not from the repo's
data: the end page carries `data-role="sale-over"`. The stub answers like Pages does for
`_redirects`, because the redirects are part of what the end deploy has to do.
"""

import copy
import functools
import http.server
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
import yaml
from pages_stub import MissingPath

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR

ROOT = Path(__file__).resolve().parents[1]
BUILT = ROOT / "build" / "public"
pytestmark = pytest.mark.skipif(not (BUILT / "styles.css").exists(), reason="site not built")


class EndDeployment(MissingPath, http.server.SimpleHTTPRequestHandler):
    redirects: dict[str, str] = {}

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self):
        for prefix, target in self.redirects.items():
            if self.path.startswith(prefix):
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()
                return
        super().do_GET()

    def log_message(self, *args):
        pass


def read_redirects(root):
    """The `/x/* /y/ 302` rules of the build's `_redirects`, as prefix -> target."""
    rules = {}
    path = root / "_redirects"
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        source, target, _status = line.split()
        rules[source.removesuffix("*")] = target
    return rules


def smoke(root):
    EndDeployment.redirects = read_redirects(root)
    handler = functools.partial(EndDeployment, directory=str(root))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            return subprocess.run(
                ["bash", "scripts/smoke.sh", f"http://127.0.0.1:{server.server_port}"],
                cwd=ROOT,
                env={**os.environ, "SMOKE_RETRIES": "0", "SMOKE_RETRY_DELAY": "1"},
                capture_output=True,
                text=True,
                timeout=120,
            )
        finally:
            server.shutdown()


@pytest.fixture
def end_site(tmp_path, monkeypatch):
    """A scratch end build with the compiled stylesheet beside it, as a deploy has it."""
    dist = tmp_path / "public"
    monkeypatch.delenv("SELLER_PHONE", raising=False)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    data = copy.deepcopy(yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8")))
    data["seller"]["sale_over"] = True
    dist.mkdir()
    shutil.copy2(BUILT / "styles.css", dist / "styles.css")
    shutil.copytree(BUILT / "fonts", dist / "fonts")
    site_builder.build_public_site(data)
    return dist


def test_smoke_passes_on_a_served_end_build(end_site):
    result = smoke(end_site)
    assert result.returncode == 0, result.stderr
    assert "smoke OK" in result.stdout


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
@pytest.mark.parametrize("scheme", ["sms:+13035550100", "tel:+13035550100"])
def test_smoke_fails_when_the_end_page_carries_a_contact_link(end_site, page, scheme):
    path = end_site / page
    html = path.read_text(encoding="utf-8")
    path.write_text(
        html.replace("</main>", f'<a href="{scheme}">text</a></main>'), encoding="utf-8"
    )
    result = smoke(end_site)
    assert result.returncode != 0
    assert "SMOKE FAIL" in result.stderr
    assert "sms:" in result.stderr or "tel:" in result.stderr


def test_smoke_fails_when_an_old_share_link_does_not_redirect(end_site):
    (end_site / "_redirects").unlink()
    result = smoke(end_site)
    assert result.returncode != 0
    assert "redirect" in result.stderr


def test_smoke_fails_when_the_spanish_page_is_not_the_end_page(end_site):
    (end_site / "es" / "index.html").write_text("<html><body>Catalog</body></html>")
    result = smoke(end_site)
    assert result.returncode != 0
    assert "SMOKE FAIL" in result.stderr


def test_smoke_fails_when_the_end_page_loses_its_stylesheet(end_site):
    (end_site / "styles.css").unlink()
    result = smoke(end_site)
    assert result.returncode != 0
    assert "stylesheet" in result.stderr


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
@pytest.mark.parametrize("number", ["(303) 555-0100", "303-555-0100", "303.555.0100", "3035550100"])
def test_smoke_fails_when_a_phone_number_is_written_out_on_the_end_page(end_site, page, number):
    path = end_site / page
    html = path.read_text(encoding="utf-8")
    path.write_text(html.replace("</main>", f"<p>Call {number}</p></main>"), encoding="utf-8")
    result = smoke(end_site)
    assert result.returncode != 0
    assert "phone number" in result.stderr


def test_smoke_fails_when_the_seller_tool_is_served(end_site):
    # An end deploy that still answers 200 at /seller/ left the tool, or a page standing in for
    # it, reachable by anyone: behind Access it is a redirect or a refusal, never a 200.
    (end_site / "seller").mkdir()
    (end_site / "seller" / "index.html").write_text("<html>tool</html>")
    result = smoke(end_site)
    assert result.returncode != 0
    assert "/seller/" in result.stderr


def test_smoke_fails_when_an_unknown_path_answers_200(end_site, monkeypatch):
    monkeypatch.setattr(EndDeployment, "spa_fallback", True)
    result = smoke(end_site)
    assert result.returncode != 0
    assert "answers 200, not 404" in result.stderr


def test_smoke_fails_when_the_end_build_has_no_not_found_page(end_site):
    (end_site / "404.html").unlink()
    result = smoke(end_site)
    assert result.returncode != 0
    assert "the 404 is not the not-found page" in result.stderr
