"""
Image Processor for Moving Sale Catalog.
Handles automatic discovery, format conversion (including HEIC), EXIF metadata scrubbing,
and optimization to a web-ready JPEG plus smaller WebP width variants.
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from leaving_denver.config import (
    DIST_DIR,
    JPEG_QUALITY,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_WIDTH,
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


def is_up_to_date(src_path: Path, target_jpg: Path) -> bool:
    """The JPEG is newer than its source and every variant its width calls for exists."""
    if not target_jpg.exists() or target_jpg.stat().st_mtime < src_path.stat().st_mtime:
        return False
    with Image.open(target_jpg) as img:
        width = img.width
    return all(variant_path(target_jpg, w).exists() for w in VARIANT_WIDTHS if w < width)


def process_image(src_path: Path, dest_path: Path) -> bool:
    """
    Applies the EXIF rotation, then drops all metadata (GPS included), scales down if
    larger than MAX bounds, and saves an optimized JPEG plus the WebP width variants.
    Skips the work when the outputs are already newer than the source.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    target_jpg = dest_path.with_suffix(".jpg")
    if is_up_to_date(src_path, target_jpg):
        return True

    # Handle HEIC files
    if src_path.suffix.lower() == ".heic":
        temp_jpg = dest_path.with_suffix(".tmp.jpg")
        if not convert_heic_to_jpg(src_path, temp_jpg):
            return False
        read_path = temp_jpg
    else:
        read_path = src_path

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
            img.save(target_jpg, "JPEG", quality=JPEG_QUALITY, optimize=True)
            for width in VARIANT_WIDTHS:
                if width >= img.width:
                    continue
                size = (width, round(img.height * width / img.width))
                variant = img.resize(size, Image.Resampling.LANCZOS)
                variant.save(
                    variant_path(target_jpg, width), "WEBP", quality=WEBP_QUALITY, method=6
                )

        if read_path != src_path and read_path.exists():
            read_path.unlink()

        return True
    except Exception as exc:
        print(f"Error processing image {src_path}: {exc}")
        return False


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
            success = process_image(photo, target_path)
            if success:
                rel_url = f"catalog/{item_id}/{target_name}"
                processed_files.append(rel_url)

        catalog_map[item_id] = processed_files

    return catalog_map
