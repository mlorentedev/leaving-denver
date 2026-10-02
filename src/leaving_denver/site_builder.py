"""
Site Builder for Denver Tech Center Moving Sale.
Compiles Single Source of Truth (data/inventory.yaml) into:
1. build/public/index.html - Sanitized, high-speed public catalog (Zero floor prices, obfuscated contacts).
   build/public/i/<id>/index.html (and es/i/<id>/) - Per-item share pages with Open Graph tags.
2. build/public/robots.txt - Link-preview fetchers and assistant fetchers allowed, every other
   crawler disallowed.
   build/public/_headers - Cloudflare Pages response headers.
   build/public/seller/index.html - The seller tool: listing copy, plus the private data as an
   encrypted envelope that only the owner's passphrase opens in the browser (ADR-007).

With `seller.sale_over: true` the public build is one "the sale is over" page per language
instead (OPS-011), and the seller tool is not built.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlsplit

import segno
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from PIL import Image

from leaving_denver.channels import RENEW_AFTER_DAYS
from leaving_denver.config import (
    BASE_DIR,
    DIST_DIR,
    INVENTORY_YAML,
    LOCALES_DIR,
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
from leaving_denver.pricing import DROP_WINDOWS
from leaving_denver.private_data import phone_parts, seller_phone
from leaving_denver.seal import validate_envelope

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


# Facebook Marketplace's condition scale; the Spanish labels live in locales/*.yaml (`conditions`).
# The car is graded on Facebook's vehicle scale instead and keeps its own wording.
CONDITIONS = ("New", "Used - Like New", "Used - Good", "Used - Fair")
# Over any of these a buyer needs a bigger car, or a second pair of hands (clearlist's thresholds).
TRUCK_SIDE_IN = 48
TRUCK_WEIGHT_LB = 50
LIFT_WEIGHT_LB = 75


def build_stylesheets() -> None:
    """Compile separate explicit template sources; never publish private template styles."""
    if not CSS_CLI.is_file():
        raise RuntimeError("Tailwind CLI missing; run npm ci before leaving-denver build")
    if not FONT_FILE.is_file():
        raise RuntimeError("Theme font missing; run npm ci before leaving-denver build")
    for source, output in (("public", DIST_DIR / "styles.css"),):
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


def sale_over(full_data: dict[str, Any]) -> bool:
    """The end-of-sale switch, `seller.sale_over` (OPS-011): off when absent. Only a boolean
    counts: YAML reads `yes` and "true" as other types, and a build that took them as off
    would keep the catalog and the phone up on the day the owner meant to close the sale."""
    seller = full_data.get("seller") or {}
    value = seller.get("sale_over", False)
    if not isinstance(value, bool):
        raise ValueError(f"seller.sale_over must be true or false, got {value!r}")
    return value


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


def list_price(item: dict[str, Any]) -> int:
    """The item's one asking price. A second price would be ambiguous and public: refused."""
    if "current_asking" in item:
        raise RuntimeError(
            f"Item {item['id']}: current_asking is gone; recommended_list_price is the one price"
        )
    if "recommended_list_price" not in item:
        raise RuntimeError(f"Item {item['id']}: recommended_list_price is required")
    return item["recommended_list_price"]


def check_condition(item: dict[str, Any]) -> str:
    """The condition, on Facebook's scale unless it is the car's."""
    condition = item.get("condition", "")
    if condition and item.get("category") != "Vehicle" and condition not in CONDITIONS:
        raise RuntimeError(
            f"Item {item['id']}: condition {condition!r} is off the scale {CONDITIONS}"
        )
    return condition


def discount_pct(item: dict[str, Any], price: int) -> int:
    """Whole percent below the retail figure, rounded down; 0 when there is nothing to claim."""
    retail = item.get("original_price", 0)
    # A used car priced against its new sticker is not a comparable; a free item has no price.
    if item.get("category") == "Vehicle" or item.get("free_with_purchase") or retail <= price:
        return 0
    return (retail - price) * 100 // retail


def positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def size_flags(item: dict[str, Any]) -> list[str]:
    """Size badges from explicit numbers in the data; the dimensions text is never parsed."""
    size, weight = item.get("size_in"), item.get("weight_lb")
    if size is not None and not (
        isinstance(size, list) and len(size) == 3 and all(positive_number(side) for side in size)
    ):
        raise RuntimeError(f"Item {item['id']}: size_in must be [w, d, h], three positive numbers")
    if weight is not None and not positive_number(weight):
        raise RuntimeError(f"Item {item['id']}: weight_lb must be a positive number")
    flags = []
    if max(size or [0]) > TRUCK_SIDE_IN or (weight or 0) > TRUCK_WEIGHT_LB:
        flags.append("truck")
    if (weight or 0) > LIFT_WEIGHT_LB:
        flags.append("lift")
    return flags


def public_item(item: dict[str, Any]) -> dict[str, Any]:
    """One published item: its id and status checked, its private fields left out."""
    # Ids become paths (i/<id>/, catalog/<id>/) and URL fragments: slugs only.
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", item["id"]):
        raise RuntimeError(f"Item id {item['id']!r} must be a lower-case slug")
    status = item.get("status", "Available")
    if status not in STATUSES:
        raise RuntimeError(f"Item {item['id']}: status {status!r} is not one of {STATUSES}")
    price = list_price(item)
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
        "condition": check_condition(item),
        "flaws": list(item.get("flaws", [])),
        # A free item keeps its list price in the data (the floors need it) but shows none.
        "price": 0 if item.get("free_with_purchase") else price,
        "discount_pct": discount_pct(item, price),
        "size_flags": size_flags(item),
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
    # Cheapest first, Sold last; sorted() is stable, so equal prices keep the data's order. A free
    # item sorts by its list price (it is free only with a purchase) so it does not lead the grid.
    shown = sorted(
        (item for item in full_data.get("items", []) if item["id"] not in hidden),
        key=lambda item: (item.get("status", "Available") == "Sold", list_price(item)),
    )
    public_items = [public_item(item) for item in shown]
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
        "payment_methods": seller["payment_methods"],
        "pickup": seller.get("pickup", []),
        "pickup_summary": seller.get("pickup_summary", ""),
    }


class SaleDates(NamedTuple):
    household: date
    vehicle: date
    schedule: dict[str, tuple[date, date]]


# The household price windows, in order; each is listed in `seller.price_schedule` by the day it opens.
SCHEDULE_WINDOWS = ("first_drop", "second_drop", "clear_floors", "giveaway")


def seller_day(seller: dict[str, Any], key: str, value: Any) -> date:
    """One date of the seller's data. Only a quoted ISO string counts: YAML reads a bare
    2026-10-23 as a date object, which `fromisoformat` rejects with a message that names no key."""
    if not isinstance(value, str):
        raise ValueError(f"seller.{key} must be a quoted YYYY-MM-DD string, got {value!r}")
    # `fromisoformat` also takes the compact 20261023, which no one reads back as this date.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"seller.{key} must be a YYYY-MM-DD date, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"seller.{key} must be a YYYY-MM-DD date, got {value!r}") from None


def sale_dates(seller: dict[str, Any]) -> SaleDates:
    """The two deadlines and the household price windows (OPS-013), checked.

    A missing or ill-ordered schedule fails the build: a drop a day late or a deadline after
    the car's is a buyer shown the wrong date. Each window runs to the day before the next one
    opens, and the last (the giveaway) to the day before the household deadline."""
    opens = seller.get("price_schedule")
    if not isinstance(opens, dict) or set(opens) != set(SCHEDULE_WINDOWS):
        raise ValueError(f"seller.price_schedule must name exactly {SCHEDULE_WINDOWS}")
    days = [seller_day(seller, f"price_schedule.{w}", opens[w]) for w in SCHEDULE_WINDOWS]
    household = seller_day(seller, "household_deadline", seller.get("household_deadline"))
    vehicle = seller_day(seller, "vehicle_deadline", seller.get("vehicle_deadline"))
    if household >= vehicle:
        raise ValueError("seller.household_deadline must be before seller.vehicle_deadline")
    ends = [*(day - timedelta(days=1) for day in days[1:]), household - timedelta(days=1)]
    if any(start > end for start, end in zip(days, ends, strict=True)):
        raise ValueError(
            "seller.price_schedule must open its windows in order, each before the next and "
            "the last before seller.household_deadline"
        )
    windows = dict(zip(SCHEDULE_WINDOWS, zip(days, ends, strict=True), strict=True))
    return SaleDates(household, vehicle, windows)


def sale_schedule(seller: dict[str, Any]) -> dict[str, tuple[date, date]]:
    """The household price windows as (first day, last day), from `seller.price_schedule`."""
    return sale_dates(seller).schedule


def for_sale(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What a buyer can still ask about: anything not Sold (Pending still counts)."""
    return [i for i in items if i["status"] != "Sold"]


def countdown_deadline(items: list[dict[str, Any]], dates: SaleDates) -> tuple[date, bool]:
    """The date the page counts down to, and whether it is the household one.

    It is the household deadline while any published household item is for sale, and the car's
    after that. Hiding the unsold household items on the day (the decommission runbook) is what
    moves it, not the calendar."""
    if any(i["category"] != "Vehicle" for i in for_sale(items)):
        return dates.household, True
    return dates.vehicle, False


def format_day(day: date, t: dict[str, Any]) -> str:
    """A date as the locale writes it: October 23, 23 de octubre."""
    return t["date_format"].format(month=t["months"][day.month], day=day.day)


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
# AI assistants fetching a page because a person asked about it (ADR-009): a buyer who pastes
# the link into one gets an answer. Their training and search crawlers are other user agents
# and stay under `*`. /seller/ is not named: Cloudflare Access guards it, and naming it here
# would advertise it.
ASSISTANT_FETCHERS = ("ChatGPT-User", "Claude-User", "Perplexity-User", "MistralAI-User")
ROBOTS_TXT = (
    "# Link-preview fetchers and assistants a person asked may read the pages;\n"
    "# every other crawler is disallowed.\n\n"
    + "".join(f"User-agent: {bot}\nAllow: /\n\n" for bot in PREVIEW_CRAWLERS)
    + "".join(f"User-agent: {bot}\nAllow: /\n\n" for bot in ASSISTANT_FETCHERS)
    + "User-agent: *\nDisallow: /\n"
)
OG_LOCALES = {"en": "en_US", "es": "es_ES"}

# The end-of-sale build (OPS-011): shared links to an item land on the end page, not a 404.
# The flyer too (FEAT-010): the paper outlives the sale, and its QR code opens the end page.
END_REDIRECTS = "/i/* / 302\n/es/i/* /es/ 302\n/flyer / 302\n/flyer/* / 302\n"
# What an end build leaves in the output root. The stylesheet step runs before the page build,
# so `styles.css` and `fonts/` are already there.
END_SITE_FILES = {
    "index.html",
    "es/index.html",
    "404.html",
    "robots.txt",
    "_headers",
    "_redirects",
    "favicon.svg",
    "styles.css",
}


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


def page_copy(vehicle: dict[str, Any] | None, items: list[dict[str, Any]]) -> dict[str, str]:
    """The locale keys for the title and the hero line: what the page still sells decides them.
    A Sold item still sits on the page, so only what a buyer can ask about counts."""
    car = vehicle is not None and vehicle["status"] != "Sold"
    stuff = bool(for_sale(items))
    key = "both" if car and stuff else "vehicle" if car else "household"
    return {"title": f"page_title_{key}", "hero": f"hero_{key}"}


def catalog_og(
    locale: str,
    t: dict[str, Any],
    vehicle: dict[str, Any] | None,
    items: list[dict[str, Any]],
    previews: dict[str, str],
    origin: str,
    countdown: str,
) -> dict[str, Any]:
    """The catalog page's own preview: the hero line and the deadline the page counts down to,
    and the vehicle's image (or the first item's with one)."""
    showcase = next((i for i in [vehicle, *items] if i and i["id"] in previews), None)
    return {
        **og_common(locale),
        "title": t[page_copy(vehicle, items)["title"]],
        "description": f"{t[page_copy(vehicle, items)['hero']]} {countdown}.",
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


LOCALIZED_FIELDS = (
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
)


def localized_flaws(item: dict[str, Any], copy: dict[str, Any], locale: str) -> list[str]:
    """The flaws in the page's language; a flaw with no Spanish line would ship in English."""
    flaws = item["flaws"]
    if locale == "en" or not flaws:
        return flaws
    spanish = copy.get("flaws", [])
    if len(spanish) != len(flaws):
        raise RuntimeError(
            f"Item {item['id']}: its {len(flaws)} flaws need the same number under es.flaws"
        )
    return spanish


def localize_item(
    item: dict[str, Any],
    source: dict[str, Any],
    locale: str,
    translations: dict[str, Any],
    asset_prefix: str,
) -> None:
    """Overlay one locale's copy and labels onto a published item, in place."""
    copy = source.get(locale, {}) if locale != "en" else {}
    if item["condition"] and item["category"] != "Vehicle":
        item["condition"] = translations["conditions"][item["condition"]]
    for source_field, public_field in LOCALIZED_FIELDS:
        if source_field in copy:
            item[public_field] = copy[source_field]
    item["flaws"] = localized_flaws(item, copy, locale)
    item["size_badges"] = [translations["size_badges"][flag] for flag in item["size_flags"]]
    item["category_label"] = translations["categories"].get(item["category"], item["category"])
    item["status_label"] = translations["statuses"][item["status"]]
    item["photos"] = [photo_set(image, asset_prefix) for image in item["images"]]
    if "verify" in item:
        localize_verify(item["verify"], copy.get("verify", {}), item["images"], asset_prefix)
    item["images"] = [asset_prefix + image for image in item["images"]]


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
        localize_item(item, source_items[item["id"]], locale, translations, asset_prefix)

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


# The languages a listing can be written in; the Spanish copy is the catalog's `es` overlay.
LISTING_LOCALES = ("en", "es")
# What the listing copy reads from an item. Nothing else of the item reaches /seller/.
SELLER_ITEM_FIELDS = (
    "id",
    "category",
    "title",
    "short_title",
    "price",
    "condition",
    "flaws",
    "dimensions",
    "specs",
    "included",
    "note",
    "pickup",
    "images",
    "year",
    "odometer",
    "title_status",
    "vin",
)
# The fields the Spanish overlay replaces; the rest of the item reads the same in both.
SELLER_COPY_FIELDS = (
    "title",
    "short_title",
    "condition",
    "flaws",
    "dimensions",
    "specs",
    "included",
    "note",
    "pickup",
    "title_status",
)
SELLER_REPLIES_YAML = BASE_DIR / "data" / "seller-replies.yaml"
REPLY_PLACEHOLDER = "{vehicle_payment}"


def seller_payment(methods: dict[str, list[str]], t: dict[str, Any], vehicle: bool) -> str:
    """Payment terms in the catalog's own words: the car's bank payments, or the household
    methods in person (see the pickup terms in index.html)."""
    if vehicle:
        return f" {t['or']} ".join(methods["vehicle"])
    return f"{', '.join(methods['household'])} {t['in_person']}"


def seller_replies(vehicle_payment: dict[str, str]) -> list[dict[str, Any]]:
    """The scam replies from data/seller-replies.yaml, each in both languages with the car's
    payment methods filled in. An entry without both languages, or with another placeholder
    left in its text, fails the build."""
    replies = []
    for reply in yaml.safe_load(SELLER_REPLIES_YAML.read_text(encoding="utf-8"))["replies"]:
        entry: dict[str, Any] = {"id": reply["id"], "title": {}, "text": {}}
        for code in LISTING_LOCALES:
            copy = reply.get(code) or {}
            if not copy.get("title") or not copy.get("text"):
                raise RuntimeError(f"Reply {reply['id']}: needs a {code} title and text")
            text = " ".join(copy["text"].split()).replace(REPLY_PLACEHOLDER, vehicle_payment[code])
            if "{" in text or "}" in text:
                raise RuntimeError(f"Reply {reply['id']}: unknown placeholder in the {code} text")
            entry["title"][code] = copy["title"].strip()
            entry["text"][code] = text
        replies.append(entry)
    return replies


def seller_item(
    item: dict[str, Any],
    spanish: dict[str, Any],
    tags: list[str],
    translations: dict[str, dict[str, Any]],
    methods: dict[str, dict[str, list[str]]],
) -> dict[str, Any]:
    """One item as the copy generator reads it: its fields, its tags and payment terms, and
    under `es` the Spanish overlay with the Spanish payment terms."""
    car = item["category"] == "Vehicle"
    payload = {field: item[field] for field in SELLER_ITEM_FIELDS if field in item}
    payload["tags"] = list(tags)
    payload["payment"] = seller_payment(methods["en"], translations["en"], car)
    payload["es"] = {field: spanish[field] for field in SELLER_COPY_FIELDS}
    payload["es"]["payment"] = seller_payment(methods["es"], translations["es"], car)
    return payload


def seller_items(
    public_data: dict[str, Any],
    full_data: dict[str, Any],
    translations: dict[str, dict[str, Any]],
    methods: dict[str, dict[str, list[str]]],
) -> list[dict[str, Any]]:
    """The items that can still be listed, English with a Spanish overlay (see seller_item)."""
    localized = {
        code: {
            item["id"]: item
            for item in localize_public_inventory(
                public_data, full_data, code, translations[code], ""
            )["items"]
        }
        for code in LISTING_LOCALES
    }
    tags = {item["id"]: item.get("tags", []) for item in full_data.get("items", [])}
    return [
        seller_item(
            item, localized["es"][item["id"]], tags.get(item["id"], []), translations, methods
        )
        for item in localized["en"].values()
        if item["status"] == "Available" and not item["free"]
    ]


def seller_roster(public_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Every published item as the private views know it: id, title, category, status, the
    public price and whether it is free. Public facts only (the catalog shows all of them)."""
    return [
        {
            "id": item["id"],
            "title": item["short_title"] or item["title"] or item["id"],
            "category": item["category"],
            "status": item["status"],
            "price": item["price"],
            "free": item["free"],
        }
        for item in public_data["items"]
    ]


def seller_drops(seller: dict[str, Any]) -> dict[str, str]:
    """The day each price-drop window opens, from the seller's explicit schedule."""
    schedule = sale_schedule(seller)
    return {window: schedule[window][0].isoformat() for window in DROP_WINDOWS}


def sealed_envelope() -> str | None:
    """The SELLER_SEALED envelope as compact JSON, or None when the build has none.

    An unset or blank secret is "no private data in this build" (every PR and the test job).
    A set one that is malformed fails the build, and the message never repeats it."""
    raw = (os.environ.get("SELLER_SEALED") or "").strip()
    if not raw:
        return None
    try:
        return json.dumps(validate_envelope(raw), separators=(",", ":"))
    except ValueError as err:
        raise RuntimeError(f"SELLER_SEALED is not a valid sealed envelope: {err}") from err


def write_seller_poster(public_data: dict[str, Any], full_data: dict[str, Any]) -> None:
    """The /seller/ listing generator: the items that can still be listed, the page's
    settings and the scam replies. Public data only, and no phone (listings never carry it)."""
    poster_dir = DIST_DIR / "seller"
    poster_dir.mkdir(parents=True, exist_ok=True)
    seller = sanitize_public_seller(full_data)
    translations = {code: load_locale(code) for code in LISTING_LOCALES}
    methods = {
        code: localize_seller(seller, full_data, code, translations[code])["payment_methods"]
        for code in LISTING_LOCALES
    }
    # Listings say when the owner moves, and that is the car's month: the owner leaves in November.
    month = sale_dates(full_data["seller"]).vehicle.month
    config = {
        "origin": site_url(),
        "month": {code: translations[code]["months"][month] for code in LISTING_LOCALES},
        # For the private views, computed in the page once the data is open (ADR-007).
        "roster": seller_roster(public_data),
        "drops": seller_drops(full_data["seller"]),
        "renew_after_days": RENEW_AFTER_DAYS,
    }
    car_payment = {
        code: seller_payment(methods[code], translations[code], True) for code in LISTING_LOCALES
    }
    items = seller_items(public_data, full_data, translations, methods)

    def script_json(value: Any) -> str:
        # `<` escaped so item text cannot close the inline <script> ("</script>", "<!--").
        return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")

    (poster_dir / "index.html").write_text(
        render(
            "seller.html",
            items_json=script_json(items),
            config_json=script_json(config),
            replies=seller_replies(car_payment),
            sealed_json=sealed_envelope(),
        ),
        encoding="utf-8",
    )
    shutil.copy2(Path(__file__).parent / "assets" / "seller.mjs", poster_dir / "seller.mjs")


def sweep_to_end_site() -> None:
    """Remove everything an earlier catalog build left in the output root: photos, share pages
    and the seller tool outlive the build that wrote them."""
    for path in sorted(DIST_DIR.rglob("*"), reverse=True):
        rel = path.relative_to(DIST_DIR).as_posix()
        if rel in END_SITE_FILES or rel == "fonts" or rel.startswith("fonts/"):
            continue
        if path.is_dir():
            if not any(path.iterdir()):
                path.rmdir()
        else:
            path.unlink()


def write_not_found() -> None:
    """`404.html` (BUG-013). Without a top-level one Pages runs the site as a single-page app and
    answers every unknown path with the catalog and a 200. It takes no data at all: Pages serves
    it for any path, so it must hold no phone and no item, in either build mode."""
    copy = yaml.safe_load((LOCALES_DIR / "not_found.yaml").read_text(encoding="utf-8"))
    html = render("not_found.html", copy=copy, site_name=load_locale("en")["site_name"])
    (DIST_DIR / "404.html").write_text(html, encoding="utf-8")


def build_end_site() -> None:
    """The sale is over: one page per language, from the locale files and nothing else. No
    phone, no item and no photo goes in, so none of them needs to be at hand."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parent / "assets" / "favicon.svg", DIST_DIR / "favicon.svg")
    origin = site_url()
    for locale in ("en", "es"):
        translations = load_locale(locale)
        og = {
            **og_common(locale),
            "title": translations["sale_over_title"],
            "description": translations["sale_over_thanks"],
            "url": f"{origin}/{locale_path(locale)}",
            "image": None,
            "image_alt": "",
        }
        html = render(
            "sale_over.html",
            locale=locale,
            t=translations,
            og=og,
            asset_prefix="" if locale == "en" else "../",
            language_links=(
                {"en": "index.html", "es": "es/"} if locale == "en" else {"en": "../", "es": "./"}
            ),
        )
        target = PUBLIC_INDEX_HTML if locale == "en" else DIST_DIR / locale / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    PUBLIC_ROBOTS_TXT.write_text(ROBOTS_TXT, encoding="utf-8")
    PUBLIC_HEADERS.write_text(PAGES_HEADERS, encoding="utf-8")
    (DIST_DIR / "_redirects").write_text(END_REDIRECTS, encoding="utf-8")
    write_not_found()
    sweep_to_end_site()


# The building flyer (FEAT-010): one printable page whose QR code carries its own UTM tags (ADR-005),
# so paper shows up in the analytics as a channel of its own.
FLYER_UTM = "utm_source=flyer&utm_medium=print&utm_campaign=moving-sale"
# Medium error correction, and segno's default 4-module quiet zone: paper gets creased and shadowed.
FLYER_QR_ERROR = "m"


def flyer_url(origin: str) -> str:
    return f"{origin}/?{FLYER_UTM}"


def flyer_qr_svg(url: str, label: str) -> Markup:
    """The QR for `url` as inline SVG. It carries no size: the page's CSS gives it one."""
    code = segno.make(url, error=FLYER_QR_ERROR)
    return Markup(code.svg_inline(border=4, omitsize=True, light="#fff", title=label))


def flyer_deadline(
    copy: dict[str, str], en: dict[str, Any], dates: SaleDates, household: bool, car: bool
) -> str:
    """The flyer's one line of dates: each deadline only while something under it is for sale."""
    parts = []
    if household:
        parts.append(copy["deadline_household"].format(date=format_day(dates.household, en)))
    if car:
        parts.append(copy["deadline_car"].format(date=format_day(dates.vehicle, en)))
    line = " · ".join(parts)
    return line[:1].upper() + line[1:]


def write_flyer(public_data: dict[str, Any], dates: SaleDates, origin: str) -> None:
    """`flyer/index.html`, from the sanitized data only: what is still for sale and the two
    deadlines, never a price or a contact. Sold items are left out so the paper claims nothing gone."""
    en = load_locale("en")
    copy = yaml.safe_load((LOCALES_DIR / "flyer.yaml").read_text(encoding="utf-8"))
    on_sale = for_sale(public_data["items"])
    household = [i for i in on_sale if i["category"] != "Vehicle"]
    car = next((i for i in on_sale if i["category"] == "Vehicle"), None)
    html = render(
        "flyer.html",
        t=copy["en"],
        site_name=en["site_name"],
        deadline=flyer_deadline(copy["en"], en, dates, bool(household), car is not None),
        qr_svg=flyer_qr_svg(flyer_url(origin), copy["en"]["qr_label"]),
        address=urlsplit(origin).netloc,
        es_scan=copy["es"]["scan"],
        categories=[label for _, label in category_chips(household, en["categories"])],
        car=car["short_title"] if car else None,
    )
    target = DIST_DIR / "flyer" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def build_public_site(full_data: dict[str, Any]) -> None:
    if sale_over(full_data):
        build_end_site()
        return
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    build_sha, phone = build_identity()
    shutil.copy2(Path(__file__).parent / "assets" / "favicon.svg", DIST_DIR / "favicon.svg")
    # The template sees the sanitized data only, never full_data.
    public_data = sanitize_public_inventory(full_data)
    seller = sanitize_public_seller(full_data)
    write_seller_poster(public_data, full_data)
    dates = sale_dates(full_data["seller"])
    deadline, for_household = countdown_deadline(public_data["items"], dates)
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
        countdown = translations[
            "deadline_household" if for_household else "deadline_vehicle"
        ].format(date=format_day(deadline, translations))
        og = catalog_og(
            locale,
            translations,
            sections["vehicle"],
            sections["items"],
            previews,
            origin,
            countdown,
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
            countdown=countdown,
            countdown_date=deadline.isoformat(),
            copy=page_copy(sections["vehicle"], sections["items"]),
            vehicle_until=translations["vehicle_until"].format(
                date=format_day(dates.vehicle, translations)
            ),
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

    write_flyer(public_data, dates, origin)

    PUBLIC_ROBOTS_TXT.write_text(ROBOTS_TXT, encoding="utf-8")

    PUBLIC_HEADERS.write_text(PAGES_HEADERS, encoding="utf-8")

    write_not_found()

    # Photo sync copies every content/photos/<id>/, so drop the unpublished ones,
    # including any left from a build when the item was still published.
    for item_id in unpublished_ids(full_data):
        shutil.rmtree(DIST_DIR / "catalog" / item_id, ignore_errors=True)


# Text no public page may carry: the plaintext of the private data. The sealed envelope has none
# of it (a base64 body and a header), so it passes.
PLAINTEXT_MARKERS = ("firm_floor_price", '"sealed_at"', '"floors":', '"price_log"')
SCANNED_SUFFIXES = {".html", ".txt", ".json", ".mjs", ".js", ""}


def check_public_names() -> None:
    for path in DIST_DIR.glob("**/*"):
        name = path.name.lower()
        if path.is_file() and (
            any(word in name for word in ("poster", "panel")) or name == "inventory.json"
        ):
            raise RuntimeError(f"SECURITY LEAK: {path.name} found in public dist directory!")


def check_public_text(path: Path, ciphertext: str | None) -> None:
    """One built file: no plaintext of the private data, and the envelope only in /seller/."""
    content = path.read_text(encoding="utf-8", errors="replace")
    for marker in PLAINTEXT_MARKERS:
        if marker in content:
            raise RuntimeError(f"SECURITY LEAK: {marker} found in {path}!")
    stray = 'id="sealed"' in content or (ciphertext is not None and ciphertext in content)
    if stray and path != DIST_DIR / "seller" / "index.html":
        raise RuntimeError(f"SECURITY LEAK: the sealed envelope is outside /seller/ in {path}!")


def verify_security_guarantees() -> None:
    """Verifies that no private file, floor price or plaintext private data leaked into
    build/public/, and that the sealed envelope (ADR-007) is in /seller/index.html alone."""
    check_public_names()
    sealed = sealed_envelope()
    ciphertext = json.loads(sealed)["ct"] if sealed else None
    for path in DIST_DIR.rglob("*"):
        if path.is_file() and path.suffix in SCANNED_SUFFIXES:
            check_public_text(path, ciphertext)


def build_all() -> None:
    """Full compilation pipeline."""
    build_stylesheets()
    print("1. Loading Single Source of Truth (data/inventory.yaml)...")
    data = load_inventory_yaml()
    over = sale_over(data)

    if over:
        print("2. The sale is over: skipping photos (the end page has none).")
    else:
        print("2. Syncing and optimizing photos from content/photos/...")
        photo_map = sync_all_photos()
        # Update item photos if found
        for item in data.get("items", []):
            item_id = item.get("id")
            if photo_map.get(item_id):
                apply_photos(item, photo_map[item_id])

    # The build only reads the YAML; `leaving-denver sync` persists photo paths.

    print("3. Building sanitized public distribution (build/public/)...")
    build_public_site(data)

    print("4. Verifying security & data isolation...")
    verify_security_guarantees()

    print("Build complete: Public site ready in build/public/")
