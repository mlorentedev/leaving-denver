"""
The social images (FEAT-017): a collage for the feed and a QR story, drawn with Pillow in the
site's own font. Everything here takes the sanitized data or plain copy, never the private file;
the layout lives in the constants and pure functions below so the tests can check the pixels.
"""

from pathlib import Path
from typing import Any

import segno
from PIL import Image, ImageDraw, ImageFont, ImageOps

# The networks the social page links with; each is a `utm_source` the beacon must know (hit.js).
SOURCES = ("instagram", "facebook", "whatsapp")
SOCIAL_UTM = "utm_medium=social&utm_campaign=moving-sale"
QR_ERROR = "m"
QUIET_ZONE = 4

POST_SIZE = (1080, 1350)
STORY_SIZE = (1080, 1920)
# Instagram draws its header over the top of a story and the reply bar over the bottom.
STORY_SAFE_TOP = 250
STORY_SAFE_BOTTOM = 340
# The QR's side with its quiet zone, at most; the module size is the largest that fits.
QR_SIDE = 640
QR_TOP = 520

MARGIN = 24
GUTTER = 12
HERO_HEIGHT = 560
ROW_HEIGHT = 250
COLLAGE_MAX = 5

BACKGROUND = (251, 251, 251)
INK = (23, 23, 23)
MUTED = (82, 82, 82)
WHITE = (255, 255, 255)


def social_url(origin: str, source: str) -> str:
    return f"{origin}/?utm_source={source}&{SOCIAL_UTM}"


def load_font(path: Path, size: int, weight: int) -> ImageFont.FreeTypeFont:
    """The site's variable font at one weight. A missing font fails: Pillow's bitmap default
    would ship an image nobody meant to post."""
    font = ImageFont.truetype(str(path), size)
    font.set_variation_by_axes([weight])
    return font


def collage_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the collage shows, in order: the car while unsold, then the dearest item of each
    household category, then the next dearest, up to COLLAGE_MAX. Sold or photo-less items never."""
    candidates = sorted(
        (i for i in items if i["status"] != "Sold" and i.get("images")),
        key=lambda i: -i["price"],
    )
    cars = [i for i in candidates if i["category"] == "Vehicle"]
    household = [i for i in candidates if i["category"] != "Vehicle"]
    seen: set[str] = set()
    leaders = []
    for i in household:
        if i["category"] not in seen:
            seen.add(i["category"])
            leaders.append(i)
    rest = [i for i in household if i not in leaders]
    return (cars[:1] + leaders + rest)[:COLLAGE_MAX]


def collage_cells(count: int) -> list[tuple[int, int, int, int]]:
    """The boxes the photos fill: one large on top, the rest side by side under it."""
    right = POST_SIZE[0] - MARGIN
    bottom = MARGIN + HERO_HEIGHT + GUTTER + ROW_HEIGHT
    if count <= 1:
        return [(MARGIN, MARGIN, right, bottom)][:count]
    cells = [(MARGIN, MARGIN, right, MARGIN + HERO_HEIGHT)]
    small = count - 1
    width = (right - MARGIN - GUTTER * (small - 1)) / small
    top = MARGIN + HERO_HEIGHT + GUTTER
    for n in range(small):
        left = MARGIN + round(n * (width + GUTTER))
        cells.append((left, top, left + round(width), bottom))
    return cells


def post_lines(
    copy: dict[str, Any], address: str, categories: list[str], car: str | None
) -> list[tuple[str, int, int, tuple[int, int, int]]]:
    """The post's text under the collage, top to bottom: (text, size, weight, colour)."""
    t = copy["en"]
    lines = [(t["heading"], 76, 800, INK), (t["sub"], 40, 600, MUTED)]
    if categories:
        lines.append((f"{t['selling']} {' · '.join(categories)}", 34, 500, INK))
    if car:
        lines.append((f"{t['car'] if categories else t['car_alone']} {car}", 34, 500, INK))
    lines += [(t["photos"], 30, 600, MUTED), (address, 52, 800, INK)]
    return lines


def story_lines(copy: dict[str, Any], address: str) -> dict[str, tuple[str, int, int, Any]]:
    """The story's text: above the QR and below it."""
    t = copy["en"]
    return {
        "above": [(t["heading"], 84, 800, INK), (t["sub"], 44, 600, MUTED)],
        "below": [
            (t["scan"], 48, 700, INK),
            (address, 54, 800, INK),
            (copy["es"]["scan"], 38, 500, MUTED),
        ],
    }


def fitted(font_path: Path, text: str, size: int, weight: int, width: int):
    """The font at `size`, shrunk until the text fits `width`."""
    font = load_font(font_path, size, weight)
    while size > 12 and font.getlength(text) > width:
        size -= 2
        font = load_font(font_path, size, weight)
    return font


def draw_lines(draw, lines, font_path: Path, top: int, gap: int = 18) -> int:
    """Each line centred, one under the other from `top`; returns where the text ends."""
    width = POST_SIZE[0] - 2 * MARGIN
    for text, size, weight, colour in lines:
        font = fitted(font_path, text, size, weight, width)
        left, upper, right, lower = font.getbbox(text)
        x = (POST_SIZE[0] - (right - left)) // 2 - left
        draw.text((x, top - upper), text, font=font, fill=colour)
        top += lower - upper + gap
    return top


def render_post(photos: list[Path], lines, font_path: Path) -> Image.Image:
    canvas = Image.new("RGB", POST_SIZE, BACKGROUND)
    cells = collage_cells(len(photos))
    for photo, (left, top, right, bottom) in zip(photos, cells, strict=True):
        with Image.open(photo) as img:
            tile = ImageOps.fit(img.convert("RGB"), (right - left, bottom - top))
        canvas.paste(tile, (left, top))
    text_top = (cells[-1][3] if cells else MARGIN) + 40
    draw_lines(ImageDraw.Draw(canvas), lines, font_path, text_top)
    return canvas


def qr_geometry(modules: int) -> tuple[int, int, int]:
    """The QR symbol's top-left corner (inside its quiet zone) and its module size in pixels."""
    module = QR_SIDE // (modules + 2 * QUIET_ZONE)
    side = module * (modules + 2 * QUIET_ZONE)
    left = (STORY_SIZE[0] - side) // 2 + QUIET_ZONE * module
    return left, QR_TOP + QUIET_ZONE * module, module


def render_story(url: str, lines: dict[str, Any], font_path: Path) -> Image.Image:
    canvas = Image.new("RGB", STORY_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw_lines(draw, lines["above"], font_path, STORY_SAFE_TOP + 40)
    matrix = segno.make(url, error=QR_ERROR).matrix
    left, top, module = qr_geometry(len(matrix))
    quiet = QUIET_ZONE * module
    side = len(matrix) * module
    draw.rectangle(
        (left - quiet, top - quiet, left + side + quiet - 1, top + side + quiet - 1), WHITE
    )
    for row, line in enumerate(matrix):
        for col, dark in enumerate(line):
            if dark:
                x, y = left + col * module, top + row * module
                draw.rectangle((x, y, x + module - 1, y + module - 1), INK)
    end = draw_lines(draw, lines["below"], font_path, top + side + quiet + 40)
    if end > STORY_SIZE[1] - STORY_SAFE_BOTTOM:
        raise RuntimeError("The story's text runs into Instagram's reply bar")
    return canvas
