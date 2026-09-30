"""
Configuration and constants for Denver Tech Center Moving Sale automation.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# Core Directories
DATA_DIR = BASE_DIR / "data"
CONTENT_DIR = BASE_DIR / "content"
PHOTOS_DIR = CONTENT_DIR / "photos"
LOCALES_DIR = BASE_DIR / "locales"
DIST_DIR = BASE_DIR / "build" / "public"
DIST_PRIVATE_DIR = BASE_DIR / "build" / "private"
DOCS_DIR = BASE_DIR / "docs"

# Files
INVENTORY_YAML = DATA_DIR / "inventory.yaml"
INVENTORY_JSON_PRIVATE = DATA_DIR / "inventory.json"
PRIVATE_SOPS_YAML = DATA_DIR / "private.sops.yaml"
PUBLIC_INDEX_HTML = DIST_DIR / "index.html"
PUBLIC_ROBOTS_TXT = DIST_DIR / "robots.txt"
PUBLIC_HEADERS = DIST_DIR / "_headers"
PRIVATE_POSTER_HTML = DIST_PRIVATE_DIR / "poster_assistant.html"

# Image Processing Standards
MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 1600
JPEG_QUALITY = 85
# Widths of the WebP copies each photo also ships as (never upscaled); `srcset` picks one.
VARIANT_WIDTHS = (480, 800, 1200)
WEBP_QUALITY = 78
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
