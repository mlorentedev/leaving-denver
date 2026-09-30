"""
Responsive photos (PERF-001): each photo ships as width variants and every catalog
<img> lets the browser pick the smallest adequate one.
"""

import json
import os
import re
from html import unescape
from pathlib import Path

import pytest
from PIL import Image

from leaving_denver import image_processor, site_builder
from leaving_denver.image_processor import VARIANT_WIDTHS, process_image, variant_path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "build" / "public"
PAGES = (DIST_DIR / "index.html", DIST_DIR / "es" / "index.html")


def make_photo(path, size, orientation=None):
    """A JPEG carrying EXIF (GPS included) and, optionally, a rotation tag."""
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    exif[0x8825] = {1: "N", 2: (39.0, 36.0, 0.0)}
    if orientation:
        exif[0x0112] = orientation
    Image.new("RGB", size, (200, 120, 40)).save(path, "JPEG", exif=exif)


@pytest.fixture
def cache():
    """One build's manifest: calls within a test share it, as one `sync_all_photos` does."""
    return {}


def outputs(target):
    return [target] + [v for w in VARIANT_WIDTHS if (v := variant_path(target, w)).is_file()]


def test_wide_photo_gets_every_variant_upright_and_without_exif(tmp_path, cache):
    src, target = tmp_path / "sofa.jpg", tmp_path / "out" / "sofa.jpg"
    # 2000x2400 stored sideways (orientation 6 = rotate 90° to display): upright and
    # capped at 1600 px tall it is 1333 px wide: every variant up to 1200 applies.
    make_photo(src, (2400, 2000), orientation=6)
    assert process_image(src, target, cache)

    with Image.open(target) as img:
        assert img.height > img.width, "EXIF rotation was not applied"
    assert widths(target) == (1333, [480, 800, 1200])
    for width in (480, 800, 1200):
        with Image.open(variant_path(target, width)) as img:
            assert img.format == "WEBP"
            assert img.width == width
    for path in outputs(target):
        with Image.open(path) as img:
            assert not img.getexif(), f"{path.name} keeps EXIF"
            assert "exif" not in img.info, f"{path.name} keeps an EXIF chunk"


def test_narrow_photo_is_never_upscaled(tmp_path, cache):
    src, target = tmp_path / "topper.jpg", tmp_path / "out" / "topper.jpg"
    make_photo(src, (300, 300))
    assert process_image(src, target, cache)
    assert target.is_file()
    assert not any(variant_path(target, w).exists() for w in VARIANT_WIDTHS)


def test_up_to_date_outputs_are_not_rewritten(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    before = {p: p.stat().st_mtime_ns for p in outputs(target) if p.exists()}
    assert process_image(src, target, cache)
    assert {p: p.stat().st_mtime_ns for p in before} == before


def test_a_missing_variant_is_rebuilt(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    variant_path(target, 800).unlink()
    assert process_image(src, target, cache)
    assert variant_path(target, 800).is_file()


def test_photo_set_lists_variants_then_the_jpeg(tmp_path, monkeypatch, cache):
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    src, target = tmp_path / "raw.jpg", tmp_path / "catalog" / "tv" / "tv-1.jpg"
    make_photo(src, (1000, 500))
    assert process_image(src, target, cache)

    photo = site_builder.photo_set("catalog/tv/tv-1.jpg", "../")
    assert photo == {
        "src": "../catalog/tv/tv-1.jpg",
        "srcset": "../catalog/tv/tv-1-480w.webp 480w, ../catalog/tv/tv-1-800w.webp 800w, "
        "../catalog/tv/tv-1.jpg 1000w",
        "width": 1000,
        "height": 500,
    }


def test_a_variant_as_wide_as_the_jpeg_replaces_it_in_srcset(tmp_path, monkeypatch, cache):
    # Two candidates with one width descriptor is invalid srcset; the WebP is the lighter.
    monkeypatch.setattr(site_builder, "DIST_DIR", tmp_path)
    src, target = tmp_path / "raw.jpg", tmp_path / "catalog" / "car" / "car-1.jpg"
    make_photo(src, (2000, 1500))
    assert process_image(src, target, cache)

    photo = site_builder.photo_set("catalog/car/car-1.jpg", "")
    assert photo["src"] == "catalog/car/car-1.jpg"
    assert photo["srcset"].split(", ")[-1] == "catalog/car/car-1-1600w.webp 1600w"
    assert ".jpg" not in photo["srcset"]


def catalog_imgs(page):
    html = page.read_text(encoding="utf-8")
    return re.findall(r"<img\b[^>]*>", html), html


def attr(tag, name):
    found = re.search(rf'\s{name}="([^"]*)"', tag)
    return unescape(found.group(1)) if found else None


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_every_catalog_img_is_responsive(page):
    tags, _ = catalog_imgs(page)
    catalog = [t for t in tags if "catalog/" in (attr(t, "src") or "")]
    assert catalog, "no catalog photos rendered"
    for tag in catalog:
        for name in ("srcset", "sizes", "width", "height"):
            assert attr(tag, name), f"{name} missing on {tag}"
        for candidate in attr(tag, "srcset").split(","):
            url = candidate.split()[0]
            assert (page.parent / url).resolve().is_file(), f"srcset names a missing file: {url}"


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_vehicle_hero_loads_first(page):
    tags, _ = catalog_imgs(page)
    hero = next(t for t in tags if "2019-ford-escape" in (attr(t, "src") or ""))
    assert attr(hero, "fetchpriority") == "high"
    assert attr(hero, "loading") != "lazy"


def resolve_sizes(sizes, viewport):
    """CSS px a `sizes` value asks for at this viewport width. Only the grammar the template
    uses: `(min-width: Npx) L, ..., default`, with each length in px or vw."""
    *conditions, default = [part.strip() for part in sizes.split(",")]
    length = default
    for condition in conditions:
        found = re.fullmatch(r"\(min-width: (\d+)px\) (\S+)", condition)
        assert found, f"unsupported sizes condition: {condition!r}"
        if viewport >= int(found.group(1)):
            length = found.group(2)
            break
    value = re.fullmatch(r"(\d+(?:\.\d+)?)(px|vw)", length)
    assert value, f"unsupported sizes length: {length!r}"
    number = float(value.group(1))
    return number if value.group(2) == "px" else viewport * number / 100


def test_resolve_sizes_follows_the_first_matching_condition():
    card = "(min-width: 1024px) 320px, (min-width: 640px) 31vw, 46vw"
    assert resolve_sizes(card, 390) == pytest.approx(179.4)
    assert resolve_sizes(card, 800) == pytest.approx(248)
    assert resolve_sizes(card, 1280) == 320
    assert resolve_sizes("48px", 390) == 48


def inventory(html):
    start = html.index("const INVENTORY = ") + len("const INVENTORY = ")
    return json.JSONDecoder().raw_decode(html, start)[0]


def test_item_dialog_uses_srcset():
    _, html = catalog_imgs(PAGES[0])
    # Each photo the dialog shows carries a srcset whose files exist at their stated width.
    photos = [p for item in inventory(html)["items"] for p in item.get("photos", [])]
    assert photos, "no dialog photos found in INVENTORY"
    for photo in photos:
        for candidate in photo["srcset"].split(", "):
            url, descriptor = candidate.split()
            with Image.open(DIST_DIR / url) as img:
                assert f"{img.width}w" == descriptor, candidate
    # The script hands those srcsets over as they are, with a sizes it can resolve.
    assignments = dict(re.findall(r"(\w+)\.srcset = ([^;]+);", html))
    assert assignments == {"mainImg": "p ? p.srcset : ''", "thumb": "p.srcset"}, assignments
    sizes = dict(re.findall(r"(\w+)\.sizes = '([^']*)';", html))
    assert set(sizes) == {"mainImg", "thumb"}, sizes
    assert resolve_sizes(sizes["mainImg"], 390) == 390
    assert resolve_sizes(sizes["thumb"], 390) == 48


def pick(srcset, needed):
    """The candidate a browser takes: the smallest at least `needed` px wide, else the largest."""
    candidates = sorted(
        (int(c.split()[1][:-1]), c.split()[0]) for c in srcset.split(",") if c.strip()
    )
    return next((url for w, url in candidates if w >= needed), candidates[-1][1])


def cover_weights(tags, viewport, dpr):
    """Bytes the covers (vehicle hero and cards) cost as the browser picks them from
    `sizes` at this viewport and DPR, against the bytes of their full JPEGs."""
    covers = [t for t in tags if attr(t, "srcset") and "w-full" in (attr(t, "class") or "").split()]
    assert any(attr(t, "fetchpriority") == "high" for t in covers), "hero not measured"
    full = sum((DIST_DIR / attr(t, "src")).stat().st_size for t in covers)
    picked = sum(
        (DIST_DIR / pick(attr(t, "srcset"), resolve_sizes(attr(t, "sizes"), viewport) * dpr))
        .stat()
        .st_size
        for t in covers
    )
    return picked, full


# Largest share of the full JPEGs a phone may download, by (viewport, DPR). DPR 2 is the
# PERF-001 budget; DPR 3 phones take a size up, and the 1600w WebP keeps the hero off the JPEG.
PHONES = {(390, 2): 1 / 3, (390, 3): 1 / 3, (430, 3): 1 / 3}


@pytest.mark.parametrize(("viewport", "dpr"), PHONES, ids=lambda v: str(v))
def test_phone_downloads_a_third_of_the_full_covers(viewport, dpr):
    tags, _ = catalog_imgs(PAGES[0])
    picked, full = cover_weights(tags, viewport, dpr)
    assert picked < full * PHONES[viewport, dpr], (
        f"{viewport} px at DPR {dpr}: covers weigh {picked} B against {full} B of full JPEGs"
    )


def test_the_budget_catches_a_card_sized_to_the_viewport():
    tags, _ = catalog_imgs(PAGES[0])
    wide = [
        re.sub(r'sizes="[^"]*"', 'sizes="100vw"', t) if 'loading="lazy"' in t else t for t in tags
    ]
    picked, full = cover_weights(wide, 390, 3)
    assert picked >= full * PHONES[390, 3]


def test_a_dpr3_phone_never_falls_back_to_the_hero_jpeg():
    tags, _ = catalog_imgs(PAGES[0])
    [hero] = [t for t in tags if attr(t, "fetchpriority") == "high"]
    for viewport in (390, 430):
        needed = resolve_sizes(attr(hero, "sizes"), viewport) * 3
        chosen = pick(attr(hero, "srcset"), needed)
        assert chosen.endswith(".webp"), f"{viewport} px at DPR 3 picks {chosen}"
        assert (DIST_DIR / chosen).stat().st_size < (DIST_DIR / attr(hero, "src")).stat().st_size


def widths(target):
    with Image.open(target) as img:
        return img.width, [w for w in VARIANT_WIDTHS if variant_path(target, w).is_file()]


def test_a_replaced_source_with_an_older_mtime_is_rebuilt(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    # `mv`, `cp -p` and `rsync -t` keep the new photo's own, older, timestamp.
    stamp = target.stat().st_mtime_ns - 10**10
    make_photo(src, (700, 500))
    os.utime(src, ns=(stamp, stamp))
    assert process_image(src, target, cache)
    assert widths(target) == (700, [480])


def inodes(target):
    return {p.name: p.stat().st_ino for p in outputs(target)}


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("MAX_IMAGE_WIDTH", 1000),
        ("MAX_IMAGE_HEIGHT", 600),
        ("JPEG_QUALITY", 50),
        ("WEBP_QUALITY", 40),
        ("VARIANT_WIDTHS", (480, 800)),
    ],
)
def test_a_settings_change_rebuilds_the_outputs(tmp_path, cache, monkeypatch, setting, value):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    before = inodes(target)
    monkeypatch.setattr(image_processor, setting, value)
    assert process_image(src, target, cache)
    # A rewrite renames a fresh file into place, so every surviving output has a new inode.
    after = inodes(target)
    assert after and all(after[name] != before.get(name) for name in after), setting


def test_a_killed_rebuild_never_leaves_a_fresh_entry(tmp_path, cache, monkeypatch):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    on_disk = json.loads(json.dumps(cache))  # the manifest the last finished build saved
    # The photo is swapped and the next build dies after installing its JPEG ...
    make_photo(src, (700, 500))
    real_replace = os.replace
    calls = []

    def dies_on_second_install(staged, path):
        calls.append(path)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real_replace(staged, path)

    monkeypatch.setattr(image_processor.os, "replace", dies_on_second_install)
    with pytest.raises(KeyboardInterrupt):
        process_image(src, target, cache)
    monkeypatch.setattr(image_processor.os, "replace", real_replace)
    # ... then the old photo comes back (`git checkout`): its entry must not vouch for B's JPEG.
    make_photo(src, (1300, 900))
    assert process_image(src, target, on_disk)
    assert widths(target) == (1300, [480, 800, 1200])


def test_a_failed_write_keeps_the_previous_outputs(tmp_path, cache, monkeypatch):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    before = {p.name: (p.stat().st_ino, p.read_bytes()) for p in outputs(target)}
    real_save = Image.Image.save

    def fails_on_webp(img, fp, fmt=None, **kwargs):
        if fmt == "WEBP":
            Path(fp).write_bytes(b"half a")
            raise OSError("disk full")
        return real_save(img, fp, fmt, **kwargs)

    monkeypatch.setattr(Image.Image, "save", fails_on_webp)
    make_photo(src, (700, 500))
    assert not process_image(src, target, cache)
    # Nothing is installed until every output is encoded: the old set stays whole.
    assert not list(target.parent.glob("*.tmp"))
    assert {p.name: (p.stat().st_ino, p.read_bytes()) for p in outputs(target)} == before
    assert image_processor.cache_key(target) not in cache


def test_a_null_stamp_never_vouches_for_a_missing_output(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    target.unlink()
    cache[image_processor.cache_key(target)]["outputs"] = {"desk.jpg": None}
    assert process_image(src, target, cache)
    assert target.is_file()


def test_an_unreadable_source_fails_that_photo_only(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    src.mkdir()  # reading it raises IsADirectoryError, an OSError
    assert not process_image(src, target, cache)
    assert image_processor.cache_key(target) not in cache


def test_a_failed_heic_conversion_leaves_nothing_in_the_output_dir(tmp_path, cache, monkeypatch):
    src, target = tmp_path / "car.heic", tmp_path / "out" / "car.jpg"
    src.write_bytes(b"heic bytes")
    staged = []

    def half_converted(heic, dest):
        staged.append(dest)
        dest.write_bytes(b"partial")
        return False

    monkeypatch.setattr(image_processor, "convert_heic_to_jpg", half_converted)
    assert not process_image(src, target, cache)
    assert not staged[0].is_relative_to(target.parent), "HEIC staged inside the deployed tree"
    assert not staged[0].exists()
    assert not list(target.parent.iterdir())


@pytest.mark.parametrize("damage", ["empty jpeg", "empty variant", "garbage jpeg"])
def test_a_damaged_output_is_rebuilt_not_raised(tmp_path, cache, damage):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    # What a build killed mid-write leaves behind.
    broken = variant_path(target, 800) if damage == "empty variant" else target
    broken.write_bytes(b"" if damage.startswith("empty") else b"not a jpeg")
    assert process_image(src, target, cache)
    assert widths(target) == (1300, [480, 800, 1200])
    with Image.open(variant_path(target, 800)) as img:
        img.verify()


def test_outputs_are_written_through_a_temporary_name(tmp_path, cache, monkeypatch):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    renamed = []
    real_replace = os.replace
    monkeypatch.setattr(
        image_processor.os, "replace", lambda a, b: renamed.append(Path(b)) or real_replace(a, b)
    )
    assert process_image(src, target, cache)
    assert sorted(renamed) == sorted(outputs(target))
    assert not list(target.parent.glob("*.tmp"))


def test_the_manifest_survives_a_rebuild_and_stays_out_of_public(tmp_path, monkeypatch):
    photos, dist = tmp_path / "photos", tmp_path / "public"
    manifest = tmp_path / ".photo-cache.json"
    (photos / "desk").mkdir(parents=True)
    make_photo(photos / "desk" / "desk-1.jpg", (1300, 900))
    monkeypatch.setattr(image_processor, "PHOTOS_DIR", photos)
    monkeypatch.setattr(image_processor, "DIST_DIR", dist)
    monkeypatch.setattr(image_processor, "PHOTO_CACHE", manifest)
    assert image_processor.sync_all_photos() == {"desk": ["catalog/desk/desk-1.jpg"]}
    assert list(json.loads(manifest.read_text())) == ["catalog/desk/desk-1.jpg"]
    before = {p: p.stat().st_mtime_ns for p in dist.rglob("*") if p.is_file()}
    # A write a killed build staged in the deployed tree is swept, never published.
    stray = dist / "catalog" / "desk" / "desk-1-800w.webp.tmp"
    stray.write_bytes(b"half")
    assert image_processor.sync_all_photos()
    assert not stray.exists()
    assert {p: p.stat().st_mtime_ns for p in dist.rglob("*") if p.is_file()} == before
    assert not [p for p in dist.rglob("*") if "cache" in p.name]
    # A corrupt manifest means a full rebuild, never a crash.
    manifest.write_text("{not json")
    assert image_processor.sync_all_photos()
    assert json.loads(manifest.read_text())


def test_variants_outside_the_current_widths_are_removed(tmp_path, cache):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    # Left by a build whose VARIANT_WIDTHS had 640, or by a wider earlier source.
    stale = [target.with_name("desk-640w.webp"), target.with_name("desk-1600w.webp")]
    for path in stale:
        path.write_bytes(b"old")
    assert process_image(src, target, cache)
    assert not any(path.exists() for path in stale)
    assert widths(target) == (1300, [480, 800, 1200])
