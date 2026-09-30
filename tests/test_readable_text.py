"""
Text meets WCAG AA (4.5:1) on the ground it sits on and is never under 12 px (FEAT-003).

The ratio is computed, not looked up: colours come from the compiled stylesheet (Tailwind
v4 writes its palette as oklch), alpha modifiers and `opacity-*` blend the text into its
ground, and a translucent ground blends into the one behind it (TEST-002).
"""

import math
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "leaving_denver" / "templates" / "index.html"
CSS = ROOT / "build" / "public" / "styles.css"
PAGES = (ROOT / "build" / "public" / "index.html", ROOT / "build" / "public" / "es" / "index.html")

AA = 4.5
MIN_PX = 12
# Only hover/focus states may change colour; a breakpoint colour would go unchecked below.
RESPONSIVE_COLOUR = re.compile(r"(sm|md|lg|xl|2xl):(text|bg)-(white|black|[a-z]+-\d)")
COLOUR = re.compile(
    r"(text|bg)-(?:\[(#[0-9a-fA-F]{3,6})\]|(white|black|[a-z]+-\d{2,3}))(?:/(\d+))?"
)
OPACITY = re.compile(r"opacity-(\d+)")
ARBITRARY_SIZE = re.compile(r"text-\[(\d+(?:\.\d+)?)(px|rem)\]")
VOID = {"area", "br", "hr", "img", "input", "link", "meta", "source", "wbr"}
WHITE = (1.0, 1.0, 1.0)


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def oklch_rgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """oklch -> gamma-encoded sRGB (Björn Ottosson's OKLab matrices), clipped to gamut."""
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    lms = [
        (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3,
        (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3,
        (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3,
    ]
    linear = [
        4.0767416621 * lms[0] - 3.3077115913 * lms[1] + 0.2309699292 * lms[2],
        -1.2684380046 * lms[0] + 2.6097574011 * lms[1] - 0.3413193965 * lms[2],
        -0.0041960863 * lms[0] - 0.7034186147 * lms[1] + 1.7076147010 * lms[2],
    ]

    def encode(c):
        c = min(max(c, 0.0), 1.0)
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    return tuple(encode(c) for c in linear)


def palette(css: str) -> dict[str, tuple[float, float, float]]:
    colours = {}
    for name, value in re.findall(r"--color-([\w-]+):([^;}]+)", css):
        value = value.strip()
        if value.startswith("#"):
            colours[name] = hex_rgb(value)
        elif oklch := re.fullmatch(r"oklch\(([\d.]+)%\s+([\d.]+|none)\s+([\d.]+|none)\)", value):
            lightness, chroma, hue = (0.0 if v == "none" else float(v) for v in oklch.groups())
            colours[name] = oklch_rgb(lightness / 100, chroma, hue)
    return colours


def luminance(rgb) -> float:
    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg) -> float:
    lighter, darker = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def blend(top, alpha, bottom):
    return tuple(alpha * t + (1 - alpha) * b for t, b in zip(top, bottom, strict=True))


class ContrastChecker(HTMLParser):
    """Walks rendered markup and measures each run of visible text against its ground.

    The stack carries (ground, text colour + alpha, opacity, exempt). `opacity-*` fades the
    text towards the ground it sits on, which is how it reads to the eye; screen-reader-only
    and `aria-hidden` text is exempt, as in WCAG 1.4.3."""

    def __init__(self, colours, ground=WHITE, text=((0.0, 0.0, 0.0), 1.0)):
        super().__init__()
        self.colours = colours
        self.stack = [(ground, text, 1.0, False)]
        self.skip = 0
        self.failures = []

    def colour(self, token):
        kind, hex_value, name, alpha = COLOUR.fullmatch(token).groups()
        rgb = hex_rgb(hex_value) if hex_value else self.colours.get(name)
        assert rgb, f"{token}: --color-{name} is not in the stylesheet"
        return kind, rgb, int(alpha) / 100 if alpha else 1.0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        attrs = dict(attrs)
        ground, text, opacity, exempt = self.stack[-1]
        # Hover, focus and selection states are not the resting colour.
        for token in (c for c in (attrs.get("class") or "").split() if ":" not in c):
            if COLOUR.fullmatch(token):
                kind, rgb, alpha = self.colour(token)
                if kind == "bg":
                    ground = blend(rgb, alpha, ground)
                else:
                    text = (rgb, alpha)
            elif (fade := OPACITY.fullmatch(token)) and tag not in ("img", "picture"):
                opacity *= int(fade.group(1)) / 100
            elif token == "sr-only":
                exempt = True
        exempt = exempt or attrs.get("aria-hidden") == "true"
        if tag not in VOID:
            self.stack.append((ground, text, opacity, exempt))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        if tag not in VOID and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        ground, (rgb, alpha), opacity, exempt = self.stack[-1]
        if self.skip or exempt or not data.strip():
            return
        ratio = contrast(blend(rgb, alpha * opacity, ground), ground)
        if ratio < AA:
            snippet = data.strip()[:30]
            self.failures.append(f"line {self.getpos()[0]}: {ratio:.2f}:1 {snippet!r}")


@pytest.fixture(scope="module")
def colours():
    return palette(CSS.read_text(encoding="utf-8"))


def test_palette_and_ratio_are_calibrated(colours):
    # Tailwind v4 publishes these hex equivalents of its oklch values.
    for name, hex_value in (
        ("neutral-400", "#a1a1a1"),
        ("neutral-500", "#737373"),
        ("neutral-900", "#171717"),
        ("emerald-700", "#007a55"),
    ):
        assert colours[name] == pytest.approx(hex_rgb(hex_value), abs=1.5 / 255), name
    # WCAG's reference pair: #767676 is the lightest grey that passes on white (4.54:1).
    assert contrast(hex_rgb("#767676"), WHITE) == pytest.approx(4.54, abs=0.01)


@pytest.mark.parametrize("page", PAGES, ids=["en", "es"])
def test_text_contrast_holds_on_its_ground(page, colours):
    checker = ContrastChecker(colours)
    checker.feed(page.read_text(encoding="utf-8"))
    assert not checker.failures, "\n".join(checker.failures)


@pytest.mark.parametrize(
    "markup",
    [
        '<div class="bg-neutral-900"><p class="text-neutral-500">set on a dark ground</p></div>',
        '<div class="text-neutral-500"><p class="bg-neutral-900">inherited grey</p></div>',
        '<div class="bg-neutral-900 text-neutral-400"><p class="bg-white">inherited</p></div>',
        '<div class="bg-neutral-100"><p class="text-neutral-500">4.35:1 on grey</p></div>',
        '<div class="bg-neutral-200"><p class="text-emerald-700">4.35:1 on grey</p></div>',
        '<p class="text-neutral-900/40">alpha modifier</p>',
        '<p class="text-[#999]">arbitrary hex</p>',
        '<p class="text-neutral-900 opacity-40">faded</p>',
        '<div class="bg-neutral-900"><p class="bg-white/10 text-neutral-500">tinted</p></div>',
    ],
)
def test_checker_catches_low_contrast(markup, colours):
    checker = ContrastChecker(colours)
    checker.feed(markup)
    assert checker.failures


@pytest.mark.parametrize(
    "markup",
    [
        '<p class="text-neutral-500">4.74:1 on white</p>',
        '<p class="sr-only text-neutral-300">announced only</p>',
        '<span aria-hidden="true" class="text-neutral-300">/</span>',
        '<p class="text-neutral-400 hover:text-neutral-900 bg-neutral-900">hover is not rest</p>',
        '<img class="opacity-60"><p class="text-neutral-900">a faded photo</p>',
    ],
)
def test_checker_passes_readable_or_exempt_text(markup, colours):
    checker = ContrastChecker(colours)
    checker.feed(markup)
    assert not checker.failures, checker.failures


def test_colours_do_not_change_at_breakpoints():
    hits = RESPONSIVE_COLOUR.findall(TEMPLATE.read_text(encoding="utf-8"))
    assert not hits, hits


def test_script_built_text_is_readable(colours):
    # Markup built in JS (status pills, spec bullets) is not in the rendered page. Each class
    # string is measured on its own ground, or on the white sheet it is rendered into.
    scripts = "".join(re.findall(r"<script>(.*?)</script>", TEMPLATE.read_text(), re.S))
    checked = 0
    for literal in re.findall(r"'([^'\n]*)'|`([^`]*)`", scripts):
        classes = " ".join(literal)
        if not re.search(r"(?<![\w:-])text-(\[#|white|black|[a-z]+-\d)", classes):
            continue
        checked += 1
        checker = ContrastChecker(colours)
        checker.feed(f'<p class="{classes}">x</p>')
        assert not checker.failures, (classes, checker.failures)
    assert checked, "no script-built text colour found: the pattern above has drifted"


@pytest.mark.parametrize("path", [TEMPLATE, *PAGES], ids=["template", "en", "es"])
def test_no_text_under_12px(path):
    html = path.read_text(encoding="utf-8")
    small = [
        f"{size}{unit}"
        for size, unit in ARBITRARY_SIZE.findall(html)
        if float(size) * (16 if unit == "rem" else 1) < MIN_PX
    ]
    assert not small, small
