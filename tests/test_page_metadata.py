"""What a search engine or Lighthouse reads from the catalog's head: a description, and language
alternates it can follow. The pages stay out of search on purpose (ADR-004, ADR-009: `noindex`),
so none of this is for ranking: a bad hreflang is a Lighthouse failure and a wrong alternate, a
missing description a blank snippet in the few places a link is shown as text."""

import re
from html import unescape
from pathlib import Path

import pytest

from leaving_denver import site_builder

PUBLIC = Path(__file__).resolve().parents[1] / "build" / "public"
PAGES = {"en": "index.html", "es": "es/index.html"}
pytestmark = pytest.mark.skipif(not (PUBLIC / "index.html").exists(), reason="site not built")


def head(locale):
    html = (PUBLIC / PAGES[locale]).read_text(encoding="utf-8")
    return re.search(r"<head>.*?</head>", html, re.S).group(0)


def meta(head_html, name, key="name"):
    found = re.search(rf'<meta {key}="{name}" content="([^"]*)"', head_html)
    return unescape(found.group(1)) if found else None


@pytest.mark.parametrize("locale", PAGES)
def test_the_page_has_a_description_that_is_its_preview_text(locale):
    description = meta(head(locale), "description")
    assert description, f"{locale}: no meta description"
    assert description == meta(head(locale), "og:description", key="property")


@pytest.mark.parametrize("locale", PAGES)
def test_the_alternates_are_absolute_on_the_site_origin_and_name_a_default(locale):
    origin = site_builder.site_url()
    links = dict(
        re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', head(locale))
    )
    # A relative href is what Lighthouse calls an invalid hreflang.
    assert links == {"en": f"{origin}/", "es": f"{origin}/es/", "x-default": f"{origin}/"}
