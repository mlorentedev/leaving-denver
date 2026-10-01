import json
import subprocess
from pathlib import Path

import pytest

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_poster_uses_only_published_sanitized_inventory(tmp_path, monkeypatch):
    public = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", public)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", public / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", public / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", public / "_headers")
    inventory = site_builder.load_inventory_yaml()
    for item in inventory["items"]:
        item["internal_notes"] = "private sentinel"
        item["firm_floor_price"] = 1

    site_builder.build_public_site(inventory)

    poster = (public / "seller/index.html").read_text(encoding="utf-8")
    payload = poster.split("const ITEMS = ", 1)[1].split("; window.posterItems", 1)[0]
    items = json.loads(payload)
    assert {item["id"] for item in items} == {
        item["id"] for item in inventory["items"] if item.get("published", True)
    }
    assert items and all("price" in item for item in items)
    for forbidden in ("private sentinel", "firm_floor_price", "pinGateModal", "8011"):
        assert forbidden not in poster
    assert (public / "seller/seller.mjs").is_file()
    assert (public / "seller/index.html").is_file()
    assert (public / "index.html").is_file()


def test_mobile_copy_uses_public_price_and_singular_voice():
    code = """
import { makeCopy } from './src/leaving_denver/assets/seller.mjs';
const item = { short_title: 'Desk', title: 'Wood desk', price: 90,
  category: 'Office', condition: 'Good', dimensions: '48 x 24',
  specs: ['Solid wood'], pickup: 'One flight of stairs' };
const descriptions = new Set();
for (const platform of ['fb', 'cl', 'offerup', 'nextdoor']) {
  const copy = makeCopy(item, platform);
  if (!copy.title.includes('Desk') || !copy.description.includes('$90') ||
      !copy.description.includes('One flight of stairs') ||
      /\\b(we|our|we'll)\\b/i.test(copy.description)) process.exit(1);
  if (platform === 'offerup' && copy.title.length > 60) process.exit(1);
  descriptions.add(copy.description);
}
if (descriptions.size < 3) process.exit(1);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "path",
    [
        "/seller/",
        "/seller/index.html",
        "/seller/seller.mjs",
        "/%73eller/index.html",
        "/%2573eller/index.html",
    ],
)
def test_access_middleware_fails_closed_without_configuration(path):
    code = f"""
import {{ onRequest }} from './functions/_middleware.js';
const response = await onRequest({{
  env: {{}}, request: new Request('https://leaving-denver.pages.dev{path}'),
  next: () => new Response('secret')
}});
if (response.status !== 503) process.exit(1);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_access_middleware_rejects_missing_jwt_when_configured():
    code = """
import { onRequest } from './functions/_middleware.js';
const response = await onRequest({
  env: { ACCESS_TEAM_DOMAIN: 'https://example.cloudflareaccess.com', ACCESS_AUD: 'a'.repeat(64) },
  request: new Request('https://preview.leaving-denver.pages.dev/seller/'),
  functionPath: '/', data: {}, waitUntil() {}, passThroughOnException() {},
  next: () => new Response('secret')
});
if (response.status !== 302 || !response.headers.get('Location')?.startsWith(
    'https://example.cloudflareaccess.com/')) process.exit(1);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_public_catalog_does_not_require_access():
    code = """
import { onRequest } from './functions/_middleware.js';
const response = await onRequest({
  env: {}, request: new Request('https://leaving-denver.pages.dev/'),
  next: () => new Response('public catalog')
});
if (response.status !== 200 || await response.text() !== 'public catalog') process.exit(1);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_mobile_access_setup_is_documented():
    ops = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")
    assert "Cloudflare Access" in ops
    assert "one-time" in ops
    assert "preview" in ops
    assert "anonymous" in ops
