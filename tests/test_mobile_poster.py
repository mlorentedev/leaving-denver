import subprocess
from pathlib import Path

import pytest
from sealed_helpers import json_block

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]
# Nothing the private tool owns may reach /seller/: floors, reserve, notes, the PIN, the phone.
# The phone's digits come from the SELLER_PHONE the tests set; "floor" alone is not listed
# because "Second floor, one flight of stairs" is public pickup copy.
PRIVATE_MARKERS = (
    "private sentinel",
    "firm_floor_price",
    "recommended_list_price",
    "internal_notes",
    "pinGateModal",
    "SELLER_PIN",
    "sessionStorage",
    "8011",
    "5555550100",
    "+1555",
    "reserve",
    "negotiat",
    "SELLER_PHONE",
)


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
    items = json_block(poster, "seller-items")
    assert {item["id"] for item in items} == {
        item["id"]
        for item in inventory["items"]
        if item.get("published", True)
        and item.get("status", "Available") == "Available"
        and not item.get("free_with_purchase")
    }
    assert items and all("price" in item for item in items)
    mjs = (public / "seller/seller.mjs").read_text(encoding="utf-8")
    for forbidden in PRIVATE_MARKERS:
        assert forbidden not in poster, f"{forbidden} reached /seller/"
        assert forbidden not in mjs, f"{forbidden} reached seller.mjs"
    assert (public / "seller/seller.mjs").is_file()
    assert (public / "seller/index.html").is_file()
    assert (public / "index.html").is_file()


def test_mobile_poster_does_not_offer_sold_pending_or_free_items(tmp_path, monkeypatch):
    public = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", public)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", public / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", public / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", public / "_headers")
    inventory = site_builder.load_inventory_yaml()
    candidates = [item for item in inventory["items"] if item.get("published", True)]
    assert len(candidates) >= 4
    for item, status in zip(candidates[:3], ["Sold", "Pending", "Available"], strict=True):
        item["status"] = status
    candidates[2]["free_with_purchase"] = True
    candidates[3]["status"] = "Available"

    site_builder.build_public_site(inventory)

    poster = (public / "seller/index.html").read_text(encoding="utf-8")
    ids = {item["id"] for item in json_block(poster, "seller-items")}
    assert not ids.intersection({item["id"] for item in candidates[:3]})
    assert candidates[3]["id"] in ids


def test_mobile_copy_uses_public_price_and_singular_voice():
    code = """
import { makeCopy } from './src/leaving_denver/assets/seller.mjs';
const item = { id: 'wood-desk', short_title: 'Desk', title: 'Wood desk', price: 90,
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


def test_mobile_copy_links_to_each_public_item_with_platform_attribution():
    code = """
import { makeCopy } from './src/leaving_denver/assets/seller.mjs';
const item = { id: 'wood-desk', title: 'Wood desk', price: 90 };
for (const [platform, source] of Object.entries({
  fb: 'facebook', cl: 'craigslist', offerup: 'offerup', nextdoor: 'nextdoor'
})) {
  const copy = makeCopy(item, platform);
  const url = new URL(copy.link);
  if (url.origin !== 'https://leaving-denver.pages.dev' ||
      url.pathname !== '/i/wood-desk/' ||
      url.searchParams.get('utm_source') !== source ||
      url.searchParams.get('utm_campaign') !== 'moving-sale') process.exit(1);
}
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    template = (ROOT / "src/leaving_denver/templates/seller.html").read_text(encoding="utf-8")
    assert 'id="link"' in template
    assert 'data-copy="link"' in template


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


def test_access_middleware_requires_signed_jwt_audience_and_expiration():
    code = """
import { onRequest } from './functions/_middleware.js';
const domain = 'https://example.cloudflareaccess.com';
const aud = 'a'.repeat(64);
const pair = await crypto.subtle.generateKey({
  name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048,
  publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256'
}, true, ['sign', 'verify']);
const jwk = { ...await crypto.subtle.exportKey('jwk', pair.publicKey),
  kid: 'test-key', alg: 'RS256' };
globalThis.fetch = async url => {
  if (url !== `${domain}/cdn-cgi/access/certs`) throw new Error('unexpected cert URL');
  return Response.json({ keys: [jwk] });
};
const encode = data => Buffer.from(JSON.stringify(data)).toString('base64url');
async function signed(payload) {
  const body = `${encode({ kid: 'test-key', alg: 'RS256' })}.${encode(payload)}`;
  const signature = await crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5', pair.privateKey, new TextEncoder().encode(body)
  );
  return `${body}.${Buffer.from(signature).toString('base64url')}`;
}
const valid = { iss: domain, aud: [aud], exp: Math.floor(Date.now() / 1000) + 3600 };
for (const [payload, expected] of [
  [valid, 200],
  [{ ...valid, aud: undefined }, 403],
  [{ ...valid, exp: undefined }, 403],
  [{ ...valid, iss: undefined }, 403],
]) {
  const response = await onRequest({
    env: { ACCESS_TEAM_DOMAIN: domain, ACCESS_AUD: aud },
    request: new Request('https://leaving-denver.pages.dev/seller/', {
      headers: { 'Cf-Access-Jwt-Assertion': await signed(payload) }
    }),
    functionPath: '/', data: {}, waitUntil() {}, passThroughOnException() {},
    next: () => new Response('seller content')
  });
  if (response.status !== expected) {
    throw new Error(`Expected ${expected}, got ${response.status} for ${JSON.stringify(payload)}`);
  }
}
const forged = (await signed(valid)).replace(/\\.[^.]+$/, '.AA');
const unsignedResponse = await onRequest({
  env: { ACCESS_TEAM_DOMAIN: domain, ACCESS_AUD: aud },
  request: new Request('https://leaving-denver.pages.dev/seller/seller.mjs', {
    headers: { 'Cf-Access-Jwt-Assertion': forged }
  }),
  functionPath: '/', data: {}, waitUntil() {}, passThroughOnException() {},
  next: () => new Response('seller content')
});
if (unsignedResponse.status !== 302) throw new Error('Forged token was accepted');
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


def test_the_local_assistant_is_gone_and_its_pin_with_it(tmp_path, monkeypatch):
    """ADR-007 retired the local workspace: no template, no built file, no PIN."""
    assert not (site_builder.TEMPLATES_DIR / "poster_assistant.html").exists()
    public = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", public)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", public / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", public / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", public / "_headers")
    site_builder.build_public_site(site_builder.load_inventory_yaml())
    assert not [p for p in public.rglob("*") if "poster" in p.name.lower()]
    site_builder.verify_security_guarantees()
