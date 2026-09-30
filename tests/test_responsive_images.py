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
    return [target] + [variant_path(target, w) for w in VARIANT_WIDTHS]


def test_wide_photo_gets_every_variant_upright_and_without_exif(tmp_path, cache):
    src, target = tmp_path / "sofa.jpg", tmp_path / "out" / "sofa.jpg"
    # 2000x2400 stored sideways (orientation 6 = rotate 90° to display): upright and
    # capped at 1600 px tall it is 1333 px wide, so every variant applies.
    make_photo(src, (2400, 2000), orientation=6)
    assert process_image(src, target, cache)

    with Image.open(target) as img:
        assert img.height > img.width, "EXIF rotation was not applied"
    for width in VARIANT_WIDTHS:
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


def test_item_dialog_uses_srcset():
    _, html = catalog_imgs(PAGES[0])
    assert "modalMainImg').srcset" in html or "mainImg.srcset" in html
    assert "thumb.srcset" in html


def pick(srcset, needed):
    """The candidate a browser takes: the smallest at least `needed` px wide, else the largest."""
    candidates = sorted(
        (int(c.split()[1][:-1]), c.split()[0]) for c in srcset.split(",") if c.strip()
    )
    return next((url for w, url in candidates if w >= needed), candidates[-1][1])


def test_phone_downloads_a_third_of_the_full_covers():
    # A 390 px phone at DPR 2: cards two per row (~180 CSS px, 360 device px), the
    # vehicle hero full width (780 device px).
    tags, _ = catalog_imgs(PAGES[0])
    covers = [t for t in tags if attr(t, "srcset") and "w-full" in (attr(t, "class") or "").split()]
    assert any(attr(t, "fetchpriority") == "high" for t in covers), "hero not measured"
    full = sum((DIST_DIR / attr(t, "src")).stat().st_size for t in covers)
    picked = sum(
        (DIST_DIR / pick(attr(t, "srcset"), 360 if attr(t, "loading") == "lazy" else 780))
        .stat()
        .st_size
        for t in covers
    )
    assert picked * 3 < full, f"phone covers weigh {picked} B against {full} B of full JPEGs"


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


def test_a_settings_change_rebuilds_the_outputs(tmp_path, cache, monkeypatch):
    src, target = tmp_path / "desk.jpg", tmp_path / "out" / "desk.jpg"
    make_photo(src, (1300, 900))
    assert process_image(src, target, cache)
    monkeypatch.setattr(image_processor, "MAX_IMAGE_WIDTH", 1000)
    assert process_image(src, target, cache)
    assert widths(target) == (1000, [480, 800])


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
    before = {p: p.stat().st_mtime_ns for p in dist.rglob("*")}
    assert image_processor.sync_all_photos()
    assert {p: p.stat().st_mtime_ns for p in dist.rglob("*")} == before
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
    assert all(variant_path(target, w).is_file() for w in VARIANT_WIDTHS)
