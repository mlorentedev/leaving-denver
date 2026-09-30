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
PAGES = {
    "index.html": ROOT / "build" / "public" / "styles.css",
    "poster_assistant.html": ROOT / "build" / "private" / "styles.css",
}

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

LITERAL = re.compile(r"'([^'\n]*)'|`([^`]*)`|\"([^\"\n]*)\"")
EXPRESSION = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\$\{.*?\}", re.S)
CLASS_STATEMENT = re.compile(r"(?:className\s*=|classList\.(?:add|remove|toggle|replace)\()([^;]*)")


def css_classes(css: str) -> set[str]:
    """Every class selector in a stylesheet, unescaped (`.md\\:flex` -> `md:flex`)."""
    names = re.findall(r"\.((?:\\.|[A-Za-z0-9_-])+)", css)
    return {re.sub(r"\\(.)", r"\1", name) for name in names}


def literal_words(text: str) -> set[str]:
    """Words of the quoted strings in a JS expression: the branches of a ternary."""
    # Compared values (`item.status === 'Sold'`) are data, not classes.
    text = re.sub(r"[!=]==?\s*(['\"`])[^'\"`]*\1", "", text)
    words = set()
    for single, template, double in LITERAL.findall(text):
        words |= class_value_words(template) if template else set((single or double).split())
    return words


def class_value_words(value: str) -> set[str]:
    """Static words of a class attribute; `${...}` branches count, Jinja is rendered instead."""
    words = set()
    for expr in EXPRESSION.findall(value):
        if expr.startswith("${"):
            words |= literal_words(expr)
    return words | set(EXPRESSION.sub(" ", value).split())


def source_tokens(template: str) -> set[str]:
    tokens = set()
    for value in re.findall(r'\bclass="([^"]*)"', template):
        tokens |= class_value_words(value)
    for statement in CLASS_STATEMENT.findall(template):
        tokens |= literal_words(statement)
    for name in class_lookups(template):
        body = re.search(rf"const {name} = \{{(.*?)\}};", template, re.S)
        assert body, f"class map {name} not found"
        tokens |= literal_words(body.group(1))
    return tokens


def class_lookups(template: str) -> set[str]:
    """Names indexed inside class statements: `... + STATUS_PILL[item.status]`."""
    names = set()
    for statement in CLASS_STATEMENT.findall(template):
        names |= set(re.findall(r"\b([A-Za-z_]\w*)\[", statement))
    return names


def rendered_tokens(html: str) -> set[str]:
    return {word for value in re.findall(r'\bclass="([^"]*)"', html) for word in value.split()}


def missing(tokens: set[str], css: str, template: str = "") -> set[str]:
    defined = css_classes(css) | HOOKS
    # The template's own `<style>`: `.hide-scrollbar { ... }`.
    for style in re.findall(r"<style>(.*?)</style>", template, re.S):
        defined |= css_classes(style)
    return {token for token in tokens if token not in defined}


def test_detector_reports_a_typo_but_not_utilities_or_hooks():
    css = r".text-neutral-500{color:red}.md\:flex{display:flex}.w-1\/2{width:50%}"
    template = (
        "<style>.hide-scrollbar{scrollbar-width:none}</style>"
        '<p class="text-netural-500 md:flex w-1/2 item-card hide-scrollbar"></p>'
        "<script>const STATUS_PILL = { Sold: 'text-neutral-500' };"
        "el.className = `p-1 ${on ? 'md:flex' : 'text-nuetral-500'}`;"
        "if (x.status === 'Sold') el.classList.add('md:flex');"
        "pill.className = 'md:flex ' + STATUS_PILL[x.status];</script>"
    )
    tokens = source_tokens(template)
    assert missing(tokens, css, template) == {"text-netural-500", "text-nuetral-500", "p-1"}


@pytest.mark.parametrize("name", ["index.html", "poster_assistant.html"])
def test_class_lookups_use_a_registered_map(name):
    template = (TEMPLATES / name).read_text(encoding="utf-8")
    lookups = class_lookups(template)
    assert lookups <= set(CLASS_MAPS), f"className built from an unregistered map: {lookups}"


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


@pytest.mark.parametrize("name", ["index.html", "poster_assistant.html"])
def test_every_class_is_covered(name, rendered):
    template = (TEMPLATES / name).read_text(encoding="utf-8")
    tokens = source_tokens(template)
    if name == "index.html":
        for html in rendered:
            tokens |= rendered_tokens(html)
    css = PAGES[name].read_text(encoding="utf-8")
    gaps = missing(tokens, css, template)
    assert not gaps, f"classes with no CSS rule (typo?): {sorted(gaps)}"
