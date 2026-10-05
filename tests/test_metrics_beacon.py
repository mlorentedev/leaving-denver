"""What the catalog template may and may not do about metrics (FEAT-015, ADR-011). The page reads
nothing of the build here, so these also run when `seller.sale_over` is on. The browser behaviour
is in test_metrics_beacon_browser.py."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "src/leaving_denver/templates/index.html").read_text(encoding="utf-8")
SHARE = (ROOT / "src/leaving_denver/templates/share.html").read_text(encoding="utf-8")
SELLER_JS = (ROOT / "src/leaving_denver/assets/seller.mjs").read_text(encoding="utf-8")


def test_the_page_has_one_beacon_call_and_it_is_to_its_own_endpoint():
    """connect-src 'self' (the CSP change) and ADR-005: no other origin, no other path."""
    calls = re.findall(r"sendBeacon\(([^,)]*)", INDEX)
    assert calls == ["'/api/hit'"]


# The handlers the page already had when the beacon was added: the count may only go down (a
# script-src policy blocks them, and the security-headers change removes them), never up.
INLINE_HANDLERS_BEFORE_THE_BEACON = 6


def test_the_page_adds_no_inline_event_handler_and_no_request_but_the_beacon():
    handlers = re.findall(r"<[a-zA-Z][^>]*\son[a-z]+\s*=", INDEX)
    assert len(handlers) <= INLINE_HANDLERS_BEFORE_THE_BEACON, "a new inline handler"
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "document.cookie", "localStorage"):
        assert forbidden not in INDEX, forbidden


def test_the_beacon_names_no_contact_data():
    """The track() helper builds the payload from the event, the source, the locale and an id."""
    helper = re.search(r"function track\(.*?\n    }\n", INDEX, re.S)
    assert helper, "stale pattern: track() not found"
    for contact in ("getSellerPhone", "_C.", "buildSmsUri", "sms:", "href"):
        assert contact not in helper.group(0), contact


def test_the_share_page_forwards_its_query_to_the_catalog():
    assert "location.search" in SHARE


def test_the_seller_tool_attributes_by_utm_source():
    """The beacon reads `utm_source`: the seller tool must keep emitting it on every link."""
    assert "utm_source=${channel.source}" in SELLER_JS


def test_the_end_page_and_the_other_pages_send_no_events():
    """Only the catalog reports. The end page (ADR-008) holds no number and calls nothing."""
    for name in ("sale_over.html", "not_found.html", "flyer.html", "seller.html"):
        text = (ROOT / "src/leaving_denver/templates" / name).read_text(encoding="utf-8")
        assert "sendBeacon" not in text and "/api/hit" not in text, name
    assert "sendBeacon" not in SELLER_JS
