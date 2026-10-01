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
# Photo freshness manifest (PERF-002): beside build/public, never deployed.
PHOTO_CACHE = BASE_DIR / "build" / ".photo-cache.json"
DOCS_DIR = BASE_DIR / "docs"

# Files
INVENTORY_YAML = DATA_DIR / "inventory.yaml"
INVENTORY_JSON_PRIVATE = DATA_DIR / "inventory.json"
PRIVATE_SOPS_YAML = DATA_DIR / "private.sops.yaml"
ASSETS_DIR = BASE_DIR / "src" / "leaving_denver" / "assets"
# The EFF large wordlist the seal draws and checks passphrases against (see its header).
WORDLIST_FILE = DATA_DIR / "eff_large_wordlist.txt"
PUBLIC_INDEX_HTML = DIST_DIR / "index.html"
PUBLIC_ROBOTS_TXT = DIST_DIR / "robots.txt"
PUBLIC_HEADERS = DIST_DIR / "_headers"
PRIVATE_POSTER_HTML = DIST_PRIVATE_DIR / "poster_assistant.html"

# Image Processing Standards
MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 1600
JPEG_QUALITY = 85
# Widths of the WebP copies each photo also ships as (never upscaled); `srcset` picks one.
# 1600 matches the JPEG cap: a 430 px phone at DPR 3 needs ~1290 px, and a WebP that wide
# weighs 0.4–0.8 of the JPEG it replaces in `srcset` (0.6 for the vehicle hero).
VARIANT_WIDTHS = (480, 800, 1200, 1600)
WEBP_QUALITY = 78
# Link previews (FEAT-002): the size Facebook, WhatsApp and X show large, and the page
# background the cover is letterboxed on.
SHARE_IMAGE_SIZE = (1200, 630)
SHARE_BACKGROUND = (251, 251, 251)
# The production origin, for the absolute URLs Open Graph needs. `SITE_URL` overrides it.
SITE_URL = "https://leaving-denver.pages.dev"
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

# Item lifecycle (FEAT-006). "Free" is a price attribute (free_with_purchase), not a status.
STATUSES = ("Available", "Pending", "Sold")

# The seller's control panel (FEAT-004): beside the private tool, never under DIST_DIR.
PRIVATE_PANEL_HTML = DIST_PRIVATE_DIR / "panel.html"
# Marks the panel's <html>; the build fails if a public page carries it.
PANEL_MARKER = "data-private-panel"
