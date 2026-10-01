"""
Site Builder for Denver Tech Center Moving Sale.
Compiles Single Source of Truth (data/inventory.yaml) into:
1. build/public/index.html - Sanitized, high-speed public catalog (Zero floor prices, obfuscated contacts).
   build/public/i/<id>/index.html (and es/i/<id>/) - Per-item share pages with Open Graph tags.
2. build/public/robots.txt - Link-preview fetchers allowed, every other crawler disallowed.
   build/public/_headers - Cloudflare Pages response headers.
3. build/private/ - Private local seller tool with multi-platform listing copy and PIN lock.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from PIL import Image

from leaving_denver.config import (
    BASE_DIR,
    DIST_DIR,
    DIST_PRIVATE_DIR,
    INVENTORY_JSON_PRIVATE,
    INVENTORY_YAML,
    LOCALES_DIR,
    PANEL_MARKER,
    PRIVATE_POSTER_HTML,
    PUBLIC_HEADERS,
    PUBLIC_INDEX_HTML,
    PUBLIC_ROBOTS_TXT,
    SHARE_IMAGE_SIZE,
    SITE_URL,
    STATUSES,
    VARIANT_WIDTHS,
)
from leaving_denver.image_processor import (
    sync_all_photos,
    synced_name,
    variant_path,
    write_share_image,
)
from leaving_denver.private_data import floors, load_private, phone_parts, seller_phone

TEMPLATES_DIR = Path(__file__).parent / "templates"
# The theme font (theme.css @font-face), copied next to each stylesheet.
FONT_FILE = (
    BASE_DIR
    / "node_modules"
    / "@fontsource-variable"
    / "plus-jakarta-sans"
    / "files"
    / "plus-jakarta-sans-latin-wght-normal.woff2"
)
CSS_CLI = (
    BASE_DIR / "node_modules" / ".bin" / ("tailwindcss.cmd" if os.name == "nt" else "tailwindcss")
)


def build_stylesheets() -> None:
    """Compile separate explicit template sources; never publish private template styles."""
    if not CSS_CLI.is_file():
        raise RuntimeError("Tailwind CLI missing; run npm ci before leaving-denver build")
    if not FONT_FILE.is_file():
        raise RuntimeError("Theme font missing; run npm ci before leaving-denver build")
    for source, output in (
        ("public", DIST_DIR / "styles.css"),
        ("private", DIST_PRIVATE_DIR / "styles.css"),
    ):
        output.parent.mkdir(parents=True, exist_ok=True)
        staged = output.with_suffix(".css.new")
        try:
            subprocess.run(
                [
                    str(CSS_CLI),
                    "-i",
                    str(BASE_DIR / "src" / "leaving_denver" / f"{source}.css"),
                    "-o",
                    str(staged),
                    "--minify",
                ],
                cwd=BASE_DIR,
                check=True,
            )
            if not staged.is_file() or not staged.stat().st_size:
                raise RuntimeError(f"Tailwind CLI produced no CSS for {source}")
            staged.replace(output)
            (output.parent / "fonts").mkdir(exist_ok=True)
            shutil.copy2(FONT_FILE, output.parent / "fonts" / FONT_FILE.name)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(f"Tailwind CSS build failed for {source}: {exc}") from exc
        finally:
            staged.unlink(missing_ok=True)


def load_inventory_yaml() -> dict[str, Any]:
    if not INVENTORY_YAML.exists():
        raise FileNotFoundError(f"SSOT inventory not found at {INVENTORY_YAML}")
    with open(INVENTORY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_inventory_yaml(data: dict[str, Any]) -> None:
    with open(INVENTORY_YAML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, indent=2)


def load_locale(locale: str) -> dict[str, Any]:
    path = LOCALES_DIR / f"{locale}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Locale not found at {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def render(template: str, **ctx: Any) -> str:
    """Render a template from TEMPLATES_DIR. A field the template uses but ctx lacks fails."""
    # Built per call, not at import, so tests can point TEMPLATES_DIR elsewhere.
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(template).render(**ctx)


def unpublished_ids(full_data: dict[str, Any]) -> set[str]:
    """Items marked `published: false`. Items publish by default."""
    return {i["id"] for i in full_data.get("items", []) if i.get("published", True) is False}


# "Verify it yourself" links go to these sites and no others (FEAT-008): a buyer follows them to
# check the VIN, so a reseller here would turn the section into the scam it warns about. Adding a
# host (Carfax, once #28 lands) is a deliberate edit to this tuple, never a data-only change.
OFFICIAL_CHECK_HOSTS = ("nhtsa.gov", "ford.com", "nicb.org")


def official_check_url(url: str) -> bool:
    """True for an https URL on an official host, with no userinfo and no characters a browser
    would read differently from `urlsplit` (backslash, whitespace, control characters)."""
    if not re.fullmatch(r"[\x21-\x7e]+", url) or "\\" in url:
        return False
    parts = urlsplit(url)
    host = parts.hostname or ""
    return (
        parts.scheme == "https"
        and parts.username is None
        and any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_CHECK_HOSTS)
    )


def public_verify(item: dict[str, Any]) -> dict[str, Any]:
    """The item's `verify:` data, checked: each check is an official https URL, each piece of
    evidence is listed in the item's `photos:` and built, and the item has a VIN to check."""
    verify = item["verify"]
    if not item.get("vin"):
        raise RuntimeError(f"{item['id']}: verify: needs the item's vin")
    # Listed, not merely synced: an unlisted photo builds too, but nobody chose to show it.
    built = {Path(image).name for image in item.get("images", [])}
    photos = {synced_name(name) for name in item.get("photos", [])} & built
    checks, evidence = [], []
    for check in verify.get("checks", []):
        if not official_check_url(check["url"]):
            raise RuntimeError(
                f"{item['id']}: check {check['id']} must be https on an official host "
                f"{OFFICIAL_CHECK_HOSTS}, got {check['url']!r}"
            )
        checks.append(
            {key: check[key] for key in ("id", "url", "label", "note")} | {"href": check["url"]}
        )
    for proof in verify.get("evidence", []):
        if synced_name(proof["photo"]) not in photos:
            raise RuntimeError(
                f"{item['id']}: evidence {proof['id']} names {proof['photo']}, "
                "which is not one of its photos"
            )
        evidence.append({key: proof[key] for key in ("id", "photo", "label", "note")})
    return {"checks": checks, "evidence": evidence}


def apply_photos(item: dict[str, Any], synced: list[str]) -> None:
    """Order an item's synced photos by its `photos:` list; the first is the cover. Unlisted
    photos follow in name order, so a newly added one still builds until it is placed."""
    if "cover" in item:
        raise RuntimeError(
            f"{item['id']}: cover: was replaced by photos:, a list whose first is the cover"
        )
    by_name = {Path(img).name: img for img in synced}
    ordered = []
    for listed in item.get("photos", []):
        name = synced_name(listed)
        if name not in by_name:
            raise RuntimeError(f"{item['id']}: photo {listed} is not among its photos")
        if by_name[name] in ordered:
            raise RuntimeError(f"{item['id']}: photo {listed} is listed twice")
        ordered.append(by_name[name])
    rest = sorted((img for img in synced if img not in ordered), key=lambda img: Path(img).name)
    images = ordered + rest
    item["images"] = images
    item["primary_image"] = images[0]


def photo_set(image: str, asset_prefix: str) -> dict[str, Any]:
    """A built photo's `<img>` attributes: its WebP variants and the JPEG itself, by width.
    A variant as wide as the JPEG takes its place: one width, one candidate."""
    jpg = DIST_DIR / image
    photo: dict[str, Any] = {
        "src": asset_prefix + image,
        "srcset": "",
        "width": None,
        "height": None,
    }
    if not jpg.is_file():
        return photo
    with Image.open(jpg) as img:
        width, height = img.size
    candidates = [
        f"{asset_prefix}{Path(image).parent.as_posix()}/{variant_path(jpg, w).name} {w}w"
        for w in VARIANT_WIDTHS
        if w <= width and variant_path(jpg, w).is_file()
    ]
    if width not in VARIANT_WIDTHS or not variant_path(jpg, width).is_file():
        candidates.append(f"{asset_prefix}{image} {width}w")
    photo.update(srcset=", ".join(candidates), width=width, height=height)
    return photo


def public_item(item: dict[str, Any]) -> dict[str, Any]:
    """One published item: its id and status checked, its private fields left out."""
    # Ids become paths (i/<id>/, catalog/<id>/) and URL fragments: slugs only.
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", item["id"]):
        raise RuntimeError(f"Item id {item['id']!r} must be a lower-case slug")
    status = item.get("status", "Available")
    if status not in STATUSES:
        raise RuntimeError(f"Item {item['id']}: status {status!r} is not one of {STATUSES}")
    pub = {
        "id": item.get("id"),
        "category": item.get("category"),
        "title": item.get("title"),
        "short_title": item.get("short_title", item.get("title")),
        "brand": item.get("brand", ""),
        "model": item.get("model", ""),
        "year": item.get("year"),
        "odometer": item.get("odometer"),
        "title_status": item.get("title_status", ""),
        "condition": item.get("condition", ""),
        # A free item keeps its list price in the data (the floors need it) but shows none.
        "price": 0
        if item.get("free_with_purchase")
        else item.get("recommended_list_price", item.get("current_asking", 0)),
        "free": bool(item.get("free_with_purchase")),
        "note": item.get("note", ""),
        "retail": item.get("original_price", 0),
        "status": status,
        "dimensions": item.get("dimensions", ""),
        "color": item.get("color", ""),
        "images": item.get("images", []),
        "specs": item.get("specs", []),
        "included": item.get("included", []),
        "pickup": item.get(
            "pickup_note", "Pickup in Denver Tech Center (DTC). Buyer must self-load."
        ),
    }
    if item.get("vin"):
        pub["vin"] = item["vin"]
    if item.get("verify"):
        pub["verify"] = public_verify(item)
    return pub


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
        public_items.append(public_item(item))

    # Sold items stay visible but go last; sorted() is stable, so the rest keep their order.
    public_items = sorted(public_items, key=lambda item: item["status"] == "Sold")
    prices = {item["id"]: item["price"] for item in public_items}
    statuses = {item["id"]: item["status"] for item in public_items}
    public_bundles = []
    for bundle in full_data.get("bundles", []):
        if hidden & set(bundle["items"]):
            continue
        missing = [i for i in bundle["items"] if i not in prices]
        if missing:
            raise RuntimeError(f"Bundle {bundle['id']} names unknown items: {missing}")
        # Totals and savings are derived here, never typed into the data.
        total = sum(prices[i] for i in bundle["items"])
        public_bundles.append(
            {
                "id": bundle["id"],
                "name": bundle.get("name", ""),
                "short_name": bundle.get("short_name", bundle.get("name", "")),
                "items": list(bundle["items"]),
                "bundle_price": bundle["bundle_price"],
                "individual_total": total,
                "savings": total - bundle["bundle_price"],
                "note": bundle.get("note", ""),
                "everything": bool(bundle.get("everything")),
                # One reserved or sold item and the bundle can no longer be bought as offered.
                "available": all(statuses[i] == "Available" for i in bundle["items"]),
            }
        )

    return {"items": public_items, "bundles": public_bundles}


def sanitize_public_seller(full_data: dict[str, Any]) -> dict[str, Any]:
    """Return only seller fields the public template is allowed to render."""
    seller = full_data["seller"]
    return {
        "location": seller["location"],
        "departure_date": seller["departure_date"],
        "payment_methods": seller["payment_methods"],
        "pickup": seller.get("pickup", []),
        "pickup_summary": seller.get("pickup_summary", ""),
    }


def sale_schedule(departure_date: str) -> dict[str, tuple[date, date]]:
    """Return the sale windows as offsets from the departure date."""
    departure = date.fromisoformat(departure_date)
    return {
        "first_drop": (departure - timedelta(days=37), departure - timedelta(days=34)),
        "second_drop": (departure - timedelta(days=25), departure - timedelta(days=23)),
        "clear_floors": (departure - timedelta(days=20), departure - timedelta(days=15)),
        "giveaway": (departure - timedelta(days=6), departure - timedelta(days=4)),
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


# Link-preview fetchers (ADR-004). They build the card a shared link shows and index
# nothing; every other crawler stays out, and X-Robots-Tag keeps pages out of search.
PREVIEW_CRAWLERS = ("facebookexternalhit", "Facebot", "Twitterbot", "TelegramBot", "WhatsApp")
ROBOTS_TXT = (
    "# Link-preview fetchers may read the pages; every other crawler is disallowed.\n\n"
    + "".join(f"User-agent: {bot}\nAllow: /\n\n" for bot in PREVIEW_CRAWLERS)
    + "User-agent: *\nDisallow: /\n"
)
OG_LOCALES = {"en": "en_US", "es": "es_ES"}


def site_url() -> str:
    """The origin Open Graph URLs are built on: `SITE_URL` from the environment, or the
    production default. A path or a trailing slash would double up in every URL."""
    url = os.environ.get("SITE_URL") or SITE_URL
    if not re.fullmatch(r"https://[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(:\d+)?", url):
        raise ValueError(f"SITE_URL must be a bare https:// origin, got {url!r}")
    return url


def share_images(items: list[dict[str, Any]]) -> dict[str, str]:
    """Each item's link-preview image, by id, as a path under build/public. Items with no
    built cover get none."""
    previews = {}
    for item in items:
        if item["images"] and (DIST_DIR / item["images"][0]).is_file():
            preview = write_share_image(DIST_DIR / item["images"][0])
            previews[item["id"]] = preview.relative_to(DIST_DIR).as_posix()
    return previews


def item_description(item: dict[str, Any], t: dict[str, Any]) -> str:
    asking = item["note"] if item["free"] else f"${item['price']:,}"
    return f"{asking} · {item['status_label']} · {t['pickup_near']}"


def locale_path(locale: str) -> str:
    """A locale's path under the site root: "" for English, "es/" for Spanish."""
    return "" if locale == "en" else f"{locale}/"


def og_common(locale: str) -> dict[str, Any]:
    width, height = SHARE_IMAGE_SIZE
    return {
        "locale": OG_LOCALES[locale],
        "locale_alternate": OG_LOCALES["es" if locale == "en" else "en"],
        "image_width": width,
        "image_height": height,
    }


def catalog_og(
    locale: str,
    t: dict[str, Any],
    vehicle: dict[str, Any] | None,
    items: list[dict[str, Any]],
    previews: dict[str, str],
    origin: str,
    departure: date,
) -> dict[str, Any]:
    """The catalog page's own preview: the hero line, and the vehicle's image (or the
    first item's with one)."""
    showcase = next((i for i in [vehicle, *items] if i and i["id"] in previews), None)
    suffix = t["hero_vehicle_suffix" if vehicle else "hero_household_suffix"]
    return {
        **og_common(locale),
        "title": t["page_title_vehicle" if vehicle else "page_title_household"],
        "description": f"{t['hero_prefix']} {t['months'][departure.month]} {suffix}",
        "url": f"{origin}/{locale_path(locale)}",
        "image": f"{origin}/{previews[showcase['id']]}" if showcase else None,
        "image_alt": showcase["title"] if showcase else "",
    }


def write_share_pages(
    locale: str,
    t: dict[str, Any],
    items: list[dict[str, Any]],
    previews: dict[str, str],
    origin: str,
) -> None:
    """One share page per published item, at i/<id>/ under the locale's path. Rebuilt
    whole, so an item unpublished since the last build loses its page."""
    share_root = DIST_DIR / locale_path(locale) / "i"
    shutil.rmtree(share_root, ignore_errors=True)
    for item in items:
        page = share_root / item["id"] / "index.html"
        page.parent.mkdir(parents=True)
        preview = previews.get(item["id"])
        og = {
            **og_common(locale),
            "title": item["title"],
            "description": item_description(item, t),
            "url": f"{origin}/{locale_path(locale)}i/{item['id']}/",
            "image": f"{origin}/{preview}" if preview else None,
            "image_alt": item["title"],
        }
        html = render("share.html", locale=locale, t=t, og=og, target=f"../../#{item['id']}")
        page.write_text(html, encoding="utf-8")


# Filter chips, in page order: category in the data -> chip label.
CHIPS = {
    "Living Room": "Living room",
    "Bedroom": "Bedroom",
    "Home Office & Tech": "Office & tech",
    "Dining & Kitchen": "Kitchen",
}


def category_chips(
    items: list[dict[str, Any]], labels: dict[str, str] = CHIPS
) -> list[tuple[str, str]]:
    """The chips for the categories present, failing on one with no chip (it would be unfilterable)."""
    present = {i["category"] for i in items}
    unknown = sorted(present - labels.keys())
    if unknown:
        raise RuntimeError(f"No filter chip for categories {unknown}: add them to CHIPS")
    return [(cat, label) for cat, label in labels.items() if cat in present]


def localize_verify(
    verify: dict[str, Any], copy: dict[str, Any], images: list[str], asset_prefix: str
) -> None:
    """Overlay one locale's labels by entry id and point each piece of evidence at its photo."""
    by_name = {Path(image).name: image for image in images}
    for entry in [*verify["checks"], *verify["evidence"]]:
        for field in ("label", "note"):
            if field in copy.get(entry["id"], {}):
                entry[field] = copy[entry["id"]][field]
        if "photo" in entry:
            entry["href"] = asset_prefix + by_name[synced_name(entry["photo"])]


def localize_public_inventory(
    public_data: dict[str, Any],
    full_data: dict[str, Any],
    locale: str,
    translations: dict[str, Any],
    asset_prefix: str,
) -> dict[str, Any]:
    """Overlay locale-specific public copy while preserving sanitized fields."""
    localized = json.loads(json.dumps(public_data))
    source_items = {item["id"]: item for item in full_data.get("items", [])}
    for item in localized["items"]:
        source = source_items[item["id"]]
        copy = source.get(locale, {}) if locale != "en" else {}
        for source_field, public_field in (
            ("title", "title"),
            ("short_title", "short_title"),
            ("specs", "specs"),
            ("included", "included"),
            ("pickup_note", "pickup"),
            ("condition", "condition"),
            ("dimensions", "dimensions"),
            ("note", "note"),
            ("title_status", "title_status"),
            ("color", "color"),
        ):
            if source_field in copy:
                item[public_field] = copy[source_field]
        item["category_label"] = translations["categories"].get(item["category"], item["category"])
        item["status_label"] = translations["statuses"][item["status"]]
        item["photos"] = [photo_set(image, asset_prefix) for image in item["images"]]
        if "verify" in item:
            localize_verify(item["verify"], copy.get("verify", {}), item["images"], asset_prefix)
        item["images"] = [asset_prefix + image for image in item["images"]]

    source_bundles = {bundle["id"]: bundle for bundle in full_data.get("bundles", [])}
    for bundle in localized["bundles"]:
        copy = source_bundles[bundle["id"]].get(locale, {}) if locale != "en" else {}
        for field in ("name", "short_name", "note"):
            if field in copy:
                bundle[field] = copy[field]
    return localized


def build_identity() -> tuple[str | None, str]:
    """The commit the footer links to and the seller's phone; a build without a phone fails."""
    build_sha = os.environ.get("GITHUB_SHA")
    if build_sha and not re.fullmatch(r"[0-9a-fA-F]{40}", build_sha):
        raise ValueError("GITHUB_SHA must be a 40-character commit hash")
    phone = seller_phone()
    if not phone:
        raise RuntimeError(
            "No seller phone: set SELLER_PHONE or make data/private.sops.yaml decryptable"
        )
    return build_sha, phone


def localize_seller(
    seller: dict[str, Any], full_data: dict[str, Any], locale: str, translations: dict[str, Any]
) -> dict[str, Any]:
    """The sanitized seller with the locale's pickup copy and payment labels."""
    localized = json.loads(json.dumps(seller))
    seller_copy = full_data["seller"].get(locale, {}) if locale != "en" else {}
    for field in ("pickup", "pickup_summary"):
        if field in seller_copy:
            localized[field] = seller_copy[field]
    localized["payment_methods"] = {
        kind: [translations["payment_methods"].get(method, method) for method in methods]
        for kind, methods in seller["payment_methods"].items()
    }
    return localized


def catalog_sections(localized_data: dict[str, Any]) -> dict[str, Any]:
    """The page's car, other items and bundles, with the everything bundle apart."""
    items = localized_data["items"]
    bundles = localized_data["bundles"]
    return {
        "vehicle": next((i for i in items if i["category"] == "Vehicle"), None),
        "items": [i for i in items if i["category"] != "Vehicle"],
        "bundles": [b for b in bundles if not b["everything"]],
        "everything": next((b for b in bundles if b["everything"]), None),
    }


def verify_markers(html: str, inventory_json: str, contact_json: str) -> None:
    """Fail closed: a template that stops emitting either one would ship a page
    with no items or no way to reach the seller."""
    for emitted, marker in (
        (
            f"const INVENTORY = {inventory_json};",
            "const INVENTORY = {{ inventory_json | safe }};",
        ),
        (f"const _C = {contact_json};", "const _C = {{ contact_json | safe }};"),
    ):
        if emitted not in html:
            raise RuntimeError(f"Template index.html does not emit {marker}")


def write_seller_poster(public_data: dict[str, Any]) -> None:
    """The /seller/ listing generator, fed the items that can still be listed."""
    poster_dir = DIST_DIR / "seller"
    poster_dir.mkdir(parents=True, exist_ok=True)
    listable_items = [
        item for item in public_data["items"] if item["status"] == "Available" and not item["free"]
    ]
    items_json = json.dumps(listable_items).replace("<", "\\u003c")
    (poster_dir / "index.html").write_text(
        render("seller.html", items_json=items_json), encoding="utf-8"
    )
    shutil.copy2(Path(__file__).parent / "assets" / "seller.mjs", poster_dir / "seller.mjs")


def build_public_site(full_data: dict[str, Any]) -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    build_sha, phone = build_identity()
    shutil.copy2(Path(__file__).parent / "assets" / "favicon.svg", DIST_DIR / "favicon.svg")
    # The template sees the sanitized data only, never full_data.
    public_data = sanitize_public_inventory(full_data)
    seller = sanitize_public_seller(full_data)
    write_seller_poster(public_data)
    departure = date.fromisoformat(seller["departure_date"])
    contact_json = json.dumps(phone_parts(phone))
    origin = site_url()
    previews = share_images(public_data["items"])
    for locale in ("en", "es"):
        translations = load_locale(locale)
        asset_prefix = "" if locale == "en" else "../"
        localized_data = localize_public_inventory(
            public_data, full_data, locale, translations, asset_prefix
        )
        sections = catalog_sections(localized_data)
        og = catalog_og(
            locale,
            translations,
            sections["vehicle"],
            sections["items"],
            previews,
            origin,
            departure,
        )
        # `<` escaped so item text cannot close the inline <script> ("</script>", "<!--").
        inventory_json = json.dumps(localized_data, indent=2).replace("<", "\\u003c")
        html = render(
            "index.html",
            locale=locale,
            t=translations,
            ui_json=json.dumps(translations, ensure_ascii=False).replace("<", "\\u003c"),
            asset_prefix=asset_prefix,
            build_sha=build_sha,
            inventory_json=inventory_json,
            contact_json=contact_json,
            seller=localize_seller(seller, full_data, locale, translations),
            og=og,
            departure_month=translations["months"][departure.month],
            chips=category_chips(sections["items"], translations["categories"]),
            language_links=(
                {"en": "index.html", "es": "es/"} if locale == "en" else {"en": "../", "es": "./"}
            ),
            **sections,
        )
        verify_markers(html, inventory_json, contact_json)

        target = PUBLIC_INDEX_HTML if locale == "en" else DIST_DIR / locale / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

        write_share_pages(locale, translations, localized_data["items"], previews, origin)

    PUBLIC_ROBOTS_TXT.write_text(ROBOTS_TXT, encoding="utf-8")

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
        if any(word in fname.lower() for word in ("poster", "panel")) or (
            fname.lower() == "inventory.json"
        ):
            raise RuntimeError(f"SECURITY LEAK: {fname} found in public dist directory!")

    # Check every localized public page for floor price leaks.
    for path in DIST_DIR.rglob("*.html"):
        content = path.read_text(encoding="utf-8")
        if "firm_floor_price" in content:
            raise RuntimeError(f"SECURITY LEAK: firm_floor_price found in {path}!")
        if PANEL_MARKER in content:
            raise RuntimeError(f"SECURITY LEAK: the private control panel is in {path}!")


def build_all() -> None:
    """Full compilation pipeline."""
    build_stylesheets()
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
