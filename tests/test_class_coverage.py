"""
Every class a page uses has a rule in the stylesheet it ships with (BUG-009).

Tailwind v4 drops a class it does not recognise without a word, so a typo such as
`text-netural-500` builds, deploys and ships unstyled. This test collects the class
tokens of both templates and fails on any that the compiled CSS does not define.
"""

import re
from pathlib import Path

import pytest

from leaving_denver import site_builder

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "leaving_denver" / "templates"
PUBLIC_CSS = ROOT / "build" / "public" / "styles.css"
PAGES = {
    "index.html": PUBLIC_CSS,
    "seller.html": PUBLIC_CSS,
    "sale_over.html": PUBLIC_CSS,
    # Script-only classes: the page's module is a Tailwind source too (public.css).
    "seller.mjs": PUBLIC_CSS,
    "poster_assistant.html": ROOT / "build" / "private" / "styles.css",
}
SOURCES = {"seller.mjs": ROOT / "src" / "leaving_denver" / "assets" / "seller.mjs"}

# Classes that only name elements for scripts or for the template's own <style>;
# they have no Tailwind rule on purpose.
HOOKS = {
    "bundle-card",
    "bundle-sheet",
    "copied-toast",
    "filter-btn",
    "item-card",
    "platform-tab",
    "week-tab",
}

# JS objects whose values are class lists, looked up at runtime: `STATUS_PILL[item.status]`.
CLASS_MAPS = ("STATUS_PILL",)

EXPRESSION = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\$\{.*?\}", re.S)
CLASS_ATTRIBUTE = re.compile(r"(?<![\w-])class=([\"'])(.*?)\1", re.S)
CLASS_ASSIGNMENT = re.compile(r"className\s*\+?=(?!=)|setAttribute\(\s*['\"]class['\"]\s*,")
CLASS_LIST_CALL = re.compile(r"classList\.(add|remove|toggle|replace)\(")


class Unresolved(ValueError):
    """A class expression the detector cannot read: a variable, a call, an unknown map."""


def css_classes(css: str) -> set[str]:
    """Class selectors of a stylesheet, unescaped (`.md\\:flex` -> `md:flex`).

    Only selector preludes count: a class name inside a declaration value, a string,
    a `url()` or a comment defines nothing."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"url\([^)]*\)", "url()", css)
    css = re.sub(r"(?<!\\)([\"'])(?:\\.|(?!\1).)*\1", '""', css)
    names = [
        name
        for prelude in re.findall(r"([^{};]*)\{", css)
        if not prelude.lstrip().startswith("@")
        for name in re.findall(r"\.((?:\\.|[A-Za-z0-9_-])+)", prelude)
    ]
    return {re.sub(r"\\(.)", r"\1", name) for name in names}


def string_end(text: str, i: int) -> int:
    """Index of the quote closing the JS string that opens at `i`."""
    quote, i = text[i], i + 1
    while text[i] != quote:
        if text[i] == "\\":
            i += 1
        elif quote == "`" and text.startswith("${", i):
            i = scan(text, i + 2, "}")
        i += 1
    return i


def scan(text: str, start: int, stop: str) -> int:
    """First `stop` character at bracket depth 0 and outside strings; len(text) if none."""
    depth, i = 0, start
    while i < len(text):
        char = text[i]
        if char in "'\"`":
            i = string_end(text, i)
        elif depth == 0 and char in stop:
            return i
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        i += 1
    return len(text)


def split_top(text: str, sep: str) -> list[str]:
    parts, start = [], 0
    while (end := scan(text, start, sep)) < len(text):
        parts.append(text[start:end])
        start = end + 1
    return [*parts, text[start:]]


def class_words(expr: str, maps: set[str]) -> set[str]:
    """Classes a JS class expression can produce: literals, ternary branches, `+` joins and
    registered map lookups (collected in `maps`). Anything else fails closed."""
    expr = expr.strip()
    while expr[:1] == "(" and scan(expr, 1, ")") == len(expr) - 1:
        expr = expr[1:-1].strip()
    if (mark := scan(expr, 0, "?")) < len(expr):  # the condition is data, not classes
        colon = scan(expr, mark + 1, ":")
        return class_words(expr[mark + 1 : colon], maps) | class_words(expr[colon + 1 :], maps)
    if len(parts := split_top(expr, "+")) > 1:
        return set().union(*(class_words(part, maps) for part in parts))
    if expr[:1] in "'\"" and string_end(expr, 0) == len(expr) - 1:
        return set(expr[1:-1].split())
    if expr[:1] == "`" and string_end(expr, 0) == len(expr) - 1:
        return class_value_words(expr[1:-1], maps)
    lookup = re.fullmatch(r"([A-Za-z_]\w*)\[.*\]", expr, re.S)
    if lookup and lookup.group(1) in CLASS_MAPS:
        maps.add(lookup.group(1))
        return set()
    raise Unresolved(f"cannot resolve class expression: {expr!r}")


def class_value_words(value: str, maps: set[str]) -> set[str]:
    """Static words of a class value; `${...}` is resolved, Jinja is rendered instead."""
    words = set()
    for expr in EXPRESSION.findall(value):
        if expr.startswith("${"):
            words |= class_words(expr[2:-1], maps)
    return words | set(EXPRESSION.sub(" ", value).split())


def source_tokens(template: str) -> set[str]:
    tokens, maps = set(), set()
    for _, value in CLASS_ATTRIBUTE.findall(template):
        tokens |= class_value_words(value, maps)
    for match in CLASS_ASSIGNMENT.finditer(template):
        tokens |= class_words(template[match.end() : scan(template, match.end(), ";")], maps)
    for match in CLASS_LIST_CALL.finditer(template):
        args = split_top(template[match.end() : scan(template, match.end(), ")")], ",")
        # toggle's second argument is the on/off condition.
        for arg in args[:1] if match.group(1) == "toggle" else args:
            tokens |= class_words(arg, maps)
    for name in maps:
        body = re.search(rf"const {name} = \{{(.*?)\}};", template, re.S)
        assert body, f"class map {name} not found"
        for _, value in re.findall(r"([\"'])(.*?)\1", body.group(1)):
            tokens |= set(value.split())
    return tokens


def rendered_tokens(html: str) -> set[str]:
    return {word for _, value in CLASS_ATTRIBUTE.findall(html) for word in value.split()}


def missing(tokens: set[str], css: str, template: str = "") -> set[str]:
    defined = css_classes(css) | HOOKS
    # The template's own `<style>`: `.hide-scrollbar { ... }`.
    for style in re.findall(r"<style>(.*?)</style>", template, re.S):
        defined |= css_classes(style)
    return {token for token in tokens if token not in defined}


def test_detector_reports_a_typo_but_not_utilities_or_hooks():
    css = (
        r".text-neutral-500{color:red}.md\:flex{display:flex}.w-1\/2{width:50%}"
        # Declaration values, strings and urls define nothing.
        '.other{content:".text-netural-500"}.bg{background:url(x.text-nuetral-500)}'
        r"@media (min-width:640px){.sm\:p-7{padding:1.75rem}}"
    )
    template = (
        "<style>.hide-scrollbar{scrollbar-width:none}</style>"
        '<p class="text-netural-500 md:flex w-1/2 item-card hide-scrollbar sm:p-7"></p>'
        "<i class='text-nuetral-600'></i>"
        "<script>const STATUS_PILL = { Sold: 'text-neutral-500' };"
        "el.className = `p-1 ${on ? 'md:flex' : 'text-nuetral-500'}`;"
        "if (x.status === 'Sold') el.classList.add('md:flex');"
        "el.classList.toggle('w-1/2', x.status === 'Sold');"
        "pill.className = 'md:flex ' + (on ? STATUS_PILL[x.status] : 'sm:p-7');</script>"
    )
    tokens = source_tokens(template)
    assert missing(tokens, css, template) == {
        "text-netural-500",
        "text-nuetral-500",
        "text-nuetral-600",
        "p-1",
    }


@pytest.mark.parametrize(
    "script",
    [
        "el.className = classes;",
        "el.className = `${classes}`;",
        "el.className = 'p-1 ' + pick(item);",
        "el.className = OTHER_MAP[item.status];",
        "el.classList.add(extra);",
        "el.setAttribute('class', classes);",
    ],
)
def test_detector_fails_closed_on_classes_it_cannot_read(script):
    with pytest.raises(Unresolved):
        source_tokens(f"<script>{script}</script>")


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Both locales of the real catalog, rendered as-is and with every status in play."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    html = []
    for variant, vehicle_status in (("as-is", None), ("sold", "Sold"), ("pending", "Pending")):
        dist = tmp_path_factory.mktemp(variant)
        monkeypatch.setattr(site_builder, "DIST_DIR", dist)
        monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
        monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
        monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
        inv = site_builder.load_inventory_yaml()
        if vehicle_status:
            others = [i for i in inv["items"] if i["category"] != "Vehicle"]
            others[0]["status"], others[1]["status"] = "Sold", "Pending"
            for item in inv["items"]:
                if item["category"] == "Vehicle":
                    item["status"] = vehicle_status
        site_builder.build_public_site(inv)
        html += [(dist / "index.html").read_text(encoding="utf-8")]
        html += [(dist / "es" / "index.html").read_text(encoding="utf-8")]
    monkeypatch.undo()
    return html


@pytest.mark.parametrize("name", list(PAGES))
def test_every_class_is_covered(name, rendered):
    template = SOURCES.get(name, TEMPLATES / name).read_text(encoding="utf-8")
    tokens = source_tokens(template)  # raises Unresolved on a class it cannot read
    if name == "index.html":
        for html in rendered:
            tokens |= rendered_tokens(html)
    css = PAGES[name].read_text(encoding="utf-8")
    gaps = missing(tokens, css, template)
    assert not gaps, f"classes with no CSS rule (typo?): {sorted(gaps)}"
