"""
Image Processor for Moving Sale Catalog.
Handles automatic discovery, format conversion (including HEIC), EXIF metadata scrubbing,
and optimization to a web-ready JPEG plus smaller WebP width variants.
"""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import PIL
from PIL import Image, ImageOps

from leaving_denver.config import (
    DIST_DIR,
    JPEG_QUALITY,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_WIDTH,
    PHOTO_CACHE,
    PHOTOS_DIR,
    SUPPORTED_IMAGE_EXTS,
    VARIANT_WIDTHS,
    WEBP_QUALITY,
)


def convert_heic_to_jpg(src_path: Path, dest_path: Path) -> bool:
    """Decodes HEIC image using ffmpeg and writes clean JPEG."""
    try:
        cmd = [
            "ffmpeg",
            "-i",
            str(src_path),
            "-vframes",
            "1",
            "-update",
            "1",
            str(dest_path),
            "-y",
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception as exc:
        print(f"Failed to convert HEIC {src_path}: {exc}")
        return False


def variant_path(jpg: Path, width: int) -> Path:
    """Where the `width`-px WebP copy of a processed JPEG lives: `<stem>-<width>w.webp`."""
    return jpg.with_name(f"{jpg.stem}-{width}w.webp")


def output_width(target_jpg: Path) -> int | None:
    """The built JPEG's width, or None when it is missing or unreadable (a killed build)."""
    try:
        with Image.open(target_jpg) as img:
            return img.width
    except (OSError, Image.UnidentifiedImageError):
        return None


def prune_stale_variants(target_jpg: Path) -> None:
    """Drop `<stem>-<N>w.webp` files the current JPEG and VARIANT_WIDTHS no longer call for."""
    width = output_width(target_jpg)
    if width is None:
        return
    wanted = {variant_path(target_jpg, w) for w in VARIANT_WIDTHS if w < width}
    for path in target_jpg.parent.glob(f"{target_jpg.stem}-*w.webp"):
        if path not in wanted and path.stem.removeprefix(f"{target_jpg.stem}-")[:-1].isdigit():
            path.unlink()


def fingerprint(src_path: Path) -> str:
    """The source's bytes plus every setting that shapes the outputs, and the encoder: a
    change to any of them means a rebuild, whatever the timestamps say."""
    digest = hashlib.sha256(src_path.read_bytes())
    settings = (
        MAX_IMAGE_WIDTH,
        MAX_IMAGE_HEIGHT,
        JPEG_QUALITY,
        WEBP_QUALITY,
        VARIANT_WIDTHS,
        PIL.__version__,
    )
    digest.update(json.dumps(settings).encode())
    return digest.hexdigest()


def cache_key(target_jpg: Path) -> str:
    """Manifest key: the output's path under build/public, so the checkout can move."""
    if target_jpg.is_relative_to(DIST_DIR):
        return target_jpg.relative_to(DIST_DIR).as_posix()
    return target_jpg.as_posix()


Cache = dict[str, dict]


def load_cache(path: Path) -> Cache:
    """The last build's manifest; missing or unreadable means rebuild everything."""
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cache if isinstance(cache, dict) else {}


def save_cache(cache: Cache, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".tmp")
    staged.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(staged, path)


def stamp(path: Path) -> list[int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return [stat.st_size, stat.st_mtime_ns]


def outputs_of(target_jpg: Path) -> list[Path]:
    width = output_width(target_jpg)
    variants = [variant_path(target_jpg, w) for w in VARIANT_WIDTHS if width and w < width]
    return [target_jpg, *variants]


def is_up_to_date(target_jpg: Path, digest: str, cache: Cache) -> bool:
    """The manifest holds this source and these settings for the JPEG, and every output
    it recorded is still the file it wrote (same size and mtime). Any rewrite since, by a
    build killed half-way through or by hand, makes the entry stale."""
    entry = cache.get(cache_key(target_jpg))
    if not isinstance(entry, dict) or entry.get("digest") != digest:
        return False
    recorded = entry.get("outputs")
    if not isinstance(recorded, dict) or target_jpg.name not in recorded:
        return False
    for name, value in recorded.items():
        # A stamp is [size, mtime_ns]; anything else (a null, a hand edit) is a miss.
        valid = isinstance(value, list) and len(value) == 2
        if not valid or not all(isinstance(v, int) for v in value):
            return False
        if stamp(target_jpg.with_name(name)) != value:
            return False
    return True


def process_image(src_path: Path, dest_path: Path, cache: Cache) -> bool:
    """
    Applies the EXIF rotation, then drops all metadata (GPS included), scales down if
    larger than MAX bounds, and saves an optimized JPEG plus the WebP width variants.
    Skips the work when `cache` (the build's manifest) says the outputs match this source
    and these settings; records them there once every output is in place.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    target_jpg = dest_path.with_suffix(".jpg")
    key = cache_key(target_jpg)
    try:
        digest = fingerprint(src_path)
    except OSError as exc:
        print(f"Error reading image {src_path}: {exc}")
        cache.pop(key, None)
        return False
    if is_up_to_date(target_jpg, digest, cache):
        prune_stale_variants(target_jpg)
        return True
    # Stale until every output below is written.
    cache.pop(key, None)

    # HEIC is decoded outside the deployed tree, so a failed or killed ffmpeg leaves
    # nothing there.
    with tempfile.TemporaryDirectory() as scratch:
        if src_path.suffix.lower() == ".heic":
            read_path = Path(scratch) / "decoded.jpg"
            if not convert_heic_to_jpg(src_path, read_path):
                return False
        else:
            read_path = src_path
        if not write_outputs(src_path, read_path, target_jpg):
            return False
    cache[key] = {
        "digest": digest,
        "outputs": {path.name: stamp(path) for path in outputs_of(target_jpg)},
    }
    return True


def write_outputs(src_path: Path, read_path: Path, target_jpg: Path) -> bool:
    """Encode every output beside its target first, then rename them all into place: a
    failed encode leaves the previous set whole, and nothing is ever half written. The
    `.tmp` suffix keeps staged names out of the `<stem>-*w.webp` prune glob."""
    staged: dict[Path, Path] = {}

    def stage(img: Image.Image, path: Path, fmt: str, **options) -> None:
        staged[path] = path.with_name(path.name + ".tmp")
        img.save(staged[path], fmt, **options)

    try:
        with Image.open(read_path) as img:
            # Rotation lives in EXIF, which the fresh RGB buffer below drops.
            img = ImageOps.exif_transpose(img).convert("RGB")

            # Scale down if exceeds max bounds
            if img.width > MAX_IMAGE_WIDTH or img.height > MAX_IMAGE_HEIGHT:
                ratio = min(MAX_IMAGE_WIDTH / img.width, MAX_IMAGE_HEIGHT / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save without EXIF metadata (data is completely fresh RGB)
            stage(img, target_jpg, "JPEG", quality=JPEG_QUALITY, optimize=True)
            for width in VARIANT_WIDTHS:
                if width >= img.width:
                    continue
                size = (width, round(img.height * width / img.width))
                variant = img.resize(size, Image.Resampling.LANCZOS)
                stage(
                    variant, variant_path(target_jpg, width), "WEBP", quality=WEBP_QUALITY, method=6
                )

        for path, tmp in staged.items():
            os.replace(tmp, path)
        prune_stale_variants(target_jpg)
        return True
    except Exception as exc:
        print(f"Error processing image {src_path}: {exc}")
        return False
    finally:
        for tmp in staged.values():
            tmp.unlink(missing_ok=True)


def sync_all_photos() -> dict[str, list[str]]:
    """
    Scans all item subdirectories in content/photos/<item_id>/
    processes each photo into build/public/catalog/<item_id>/
    and returns a mapping of item_id -> list of relative catalog paths.
    """
    catalog_map: dict[str, list[str]] = {}

    if not PHOTOS_DIR.exists():
        print(f"Warning: Photos directory {PHOTOS_DIR} does not exist.")
        return catalog_map

    # Writes a killed build staged under the deployed tree are never published.
    for staged in (DIST_DIR / "catalog").glob("**/*.tmp"):
        staged.unlink()
    cache = load_cache(PHOTO_CACHE)
    for item_dir in sorted(PHOTOS_DIR.iterdir()):
        if not item_dir.is_dir():
            continue

        item_id = item_dir.name
        dest_item_dir = DIST_DIR / "catalog" / item_id
        processed_files: list[str] = []

        for photo in sorted(item_dir.iterdir()):
            if photo.suffix.lower() not in SUPPORTED_IMAGE_EXTS:
                continue

            target_name = photo.stem.lower().replace(" ", "_") + ".jpg"
            target_path = dest_item_dir / target_name

            # Process / update image
            success = process_image(photo, target_path, cache)
            if success:
                rel_url = f"catalog/{item_id}/{target_name}"
                processed_files.append(rel_url)

        catalog_map[item_id] = processed_files

    save_cache(cache, PHOTO_CACHE)
    return catalog_map
