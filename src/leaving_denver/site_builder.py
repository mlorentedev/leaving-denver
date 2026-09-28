"""
Site Builder for Denver Tech Center Moving Sale.
Compiles Single Source of Truth (data/inventory.yaml) into:
1. build/public/index.html - Sanitized, high-speed public catalog (Zero floor prices, obfuscated contacts).
2. build/public/robots.txt - Total crawler disallow directive.
   build/public/_headers - Cloudflare Pages response headers.
3. build/private/ - Private local seller tool with multi-platform listing copy and PIN lock.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from leaving_denver.config import (
    DIST_DIR,
    DIST_PRIVATE_DIR,
    INVENTORY_JSON_PRIVATE,
    INVENTORY_YAML,
    PRIVATE_POSTER_HTML,
    PUBLIC_HEADERS,
    PUBLIC_INDEX_HTML,
    PUBLIC_ROBOTS_TXT,
)
from leaving_denver.image_processor import sync_all_photos
from leaving_denver.private_data import floors, load_private, phone_parts, seller_phone

TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_inventory_yaml() -> dict[str, Any]:
    if not INVENTORY_YAML.exists():
        raise FileNotFoundError(f"SSOT inventory not found at {INVENTORY_YAML}")
    with open(INVENTORY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_inventory_yaml(data: dict[str, Any]) -> None:
    with open(INVENTORY_YAML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, indent=2)


def render(template: str, **ctx: Any) -> str:
    """Render a template from TEMPLATES_DIR. A field the template uses but ctx lacks fails."""
    # Built per call, not at import, so tests can point TEMPLATES_DIR elsewhere.
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
    )
    return env.get_template(template).render(**ctx)


def unpublished_ids(full_data: dict[str, Any]) -> set[str]:
    """Items marked `published: false`. Items publish by default."""
    return {i["id"] for i in full_data.get("items", []) if i.get("published", True) is False}


def apply_photos(item: dict[str, Any], synced: list[str]) -> None:
    """Set an item's synced photos, its `cover:` photo first when it names one."""
    images = list(synced)
    cover = item.get("cover")
    if cover:
        # Photo sync renames files this way (image_processor.sync_all_photos).
        name = Path(cover).stem.lower().replace(" ", "_") + ".jpg"
        match = [img for img in images if Path(img).name == name]
        if not match:
            raise RuntimeError(f"{item['id']}: cover {cover} is not among its photos")
        images.remove(match[0])
        images.insert(0, match[0])
    item["images"] = images
    item["primary_image"] = images[0]


def sanitize_public_inventory(full_data: dict[str, Any]) -> dict[str, Any]:
    """
    Strips internal seller secrets:
    - firm_floor_price
    - internal negotiation notes
    and drops unpublished items, with every bundle that contains one.
    """
    hidden = unpublished_ids(full_data)
    for bundle in full_data.get("bundles", []):
        # A string would be compared character by character and never match a hidden id.
        if not isinstance(bundle.get("items"), list):
            raise RuntimeError(f"Bundle {bundle.get('id')}: items must be a list of item ids")
    public_items = []
    for item in full_data.get("items", []):
        if item["id"] in hidden:
            continue
        pub = {
            "id": item.get("id"),
            "category": item.get("category"),
            "title": item.get("title"),
            "short_title": item.get("short_title", item.get("title")),
            "brand": item.get("brand", ""),
            "price": item.get("recommended_list_price", item.get("current_asking", 0)),
            "retail": item.get("original_price", 0),
            "status": item.get("status", "Available"),
            "dimensions": item.get("dimensions", ""),
            "color": item.get("color", ""),
            "images": item.get("images", []),
            "specs": item.get("specs", []),
            "pickup": item.get(
                "pickup_note", "Pickup in Denver Tech Center (DTC). Buyer must self-load."
            ),
        }
        public_items.append(pub)

    return {
        "items": public_items,
        "bundles": [
            b for b in full_data.get("bundles", []) if not hidden & set(b.get("items", []))
        ],
    }


# Cloudflare Pages reads _headers from the output root. Photos keep their names
# when replaced, so they get a day of cache rather than `immutable`.
PAGES_HEADERS = """/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  X-Robots-Tag: noindex

/catalog/*
  Cache-Control: public, max-age=86400
"""


def build_public_site(full_data: dict[str, Any]) -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    phone = seller_phone()
    if not phone:
        raise RuntimeError(
            "No seller phone: set SELLER_PHONE or make data/private.sops.yaml decryptable"
        )
    # The template sees the sanitized data only, never full_data.
    inventory_json = json.dumps(sanitize_public_inventory(full_data), indent=2)
    contact_json = json.dumps(phone_parts(phone))
    html = render("index.html", inventory_json=inventory_json, contact_json=contact_json)

    # Fail closed: a template that stops emitting either one would ship a page
    # with no items or no way to reach the seller.
    for emitted, marker in (
        (f"const INVENTORY = {inventory_json};", "const INVENTORY = {{ inventory_json | safe }};"),
        (f"const _C = {contact_json};", "const _C = {{ contact_json | safe }};"),
    ):
        if emitted not in html:
            raise RuntimeError(f"Template index.html does not emit {marker}")

    with open(PUBLIC_INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    # Write robots.txt
    with open(PUBLIC_ROBOTS_TXT, "w", encoding="utf-8") as f:
        f.write("# Disallow all automated crawlers and scrapers\nUser-agent: *\nDisallow: /\n")

    PUBLIC_HEADERS.write_text(PAGES_HEADERS, encoding="utf-8")

    # Photo sync copies every content/photos/<id>/, so drop the unpublished ones,
    # including any left from a build when the item was still published.
    for item_id in unpublished_ids(full_data):
        shutil.rmtree(DIST_DIR / "catalog" / item_id, ignore_errors=True)


def build_private_workspace(full_data: dict[str, Any]) -> None:
    private = load_private()
    if not private:
        print("   Skipped: data/private.sops.yaml is not decryptable here (expected in CI).")
        return

    DIST_PRIVATE_DIR.mkdir(parents=True, exist_ok=True)

    # Merge the encrypted reserve floors and phone back in, for local use only
    full_data = json.loads(json.dumps(full_data))
    reserve = floors(private)
    hidden = unpublished_ids(full_data)
    for item in full_data.get("items", []):
        item["draft"] = item["id"] in hidden
        if item["id"] in reserve:
            item["firm_floor_price"] = reserve[item["id"]]
    full_data.setdefault("seller", {})["phone"] = seller_phone(private)

    for target in (INVENTORY_JSON_PRIVATE, DIST_PRIVATE_DIR / "inventory.json"):
        with open(target, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2)

    template_path = TEMPLATES_DIR / "poster_assistant.html"
    if template_path.exists():
        shutil.copy2(template_path, PRIVATE_POSTER_HTML)


def verify_security_guarantees() -> None:
    """Verifies that no private files or floor prices leaked into build/public/"""
    dist_files = [f.name for f in DIST_DIR.glob("**/*") if f.is_file()]
    for fname in dist_files:
        if "poster" in fname.lower() or fname.lower() == "inventory.json":
            raise RuntimeError(f"SECURITY LEAK: {fname} found in public dist directory!")

    # Check contents of public index.html for floor price leaks
    with open(PUBLIC_INDEX_HTML, encoding="utf-8") as f:
        content = f.read()
        if "firm_floor_price" in content:
            raise RuntimeError("SECURITY LEAK: firm_floor_price found in public index.html!")


def build_all() -> None:
    """Full compilation pipeline."""
    print("1. Syncing and optimizing photos from content/photos/...")
    photo_map = sync_all_photos()

    print("2. Loading Single Source of Truth (data/inventory.yaml)...")
    data = load_inventory_yaml()

    # Update item photos if found
    for item in data.get("items", []):
        item_id = item.get("id")
        if photo_map.get(item_id):
            apply_photos(item, photo_map[item_id])

    # The build only reads the YAML; `leaving-denver sync` persists photo paths.

    print("3. Building sanitized public distribution (build/public/)...")
    build_public_site(data)

    print("4. Building private seller assistant (build/private/)...")
    build_private_workspace(data)

    print("5. Verifying security & data isolation...")
    verify_security_guarantees()

    print("Build complete: Public site ready in build/public/, private tool in build/private/")
