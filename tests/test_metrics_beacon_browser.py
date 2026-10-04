"""The first-party event beacon, run in headless Chrome over the built catalog (FEAT-015).

Two kinds of test. The first stubs `navigator.sendBeacon` before the page script and reads what the
page would have sent: the events, their order, what each tap carries, and that the sms: link is
left exactly as it was. The second serves the real build over HTTP under `connect-src 'self'` with
a stand-in for /api/hit, so the real `sendBeacon` runs and the server sees the real request: that
is what shows the beacon is same-origin (a file:// page has no policy) and that a seller-tool
share link keeps its source on the way to the catalog. Harness: browser_harness.py."""

import functools
import http.server
import json
import threading
import time

import pytest
from browser_harness import PUBLIC, needs_chrome, open_page, page_items, pointer, run_page
from pages_stub import AppliesHeadersFile, MissingPath
from test_public_csp import SETUP as CSP_SETUP
from test_public_csp import no_trouble, served_headers

pytestmark = needs_chrome

FLYER = "utm_source=flyer&utm_medium=print&utm_campaign=moving-sale"
CAR = "2019-ford-escape-sel-awd"

STUB = """
window.BEACONS = [];
navigator.sendBeacon = (url, data) => { BEACONS.push({ url, body: JSON.parse(String(data)) }); return true; };
"""
# A text link keeps its default action (the native sms: hand-off) unless the page cancelled it:
# this window listener runs after the page's, records which, and then stops the navigation itself.
CLICKS = """
window.CLICKS = [];
window.addEventListener('click', e => {
  if (!e.target.closest('a[href^="sms:"]')) return;
  CLICKS.push(e.defaultPrevented);
  e.preventDefault();
});
"""
# The item in an available bundle, and that bundle, from the page's own data.
IN_A_BUNDLE = """
const bundled = INVENTORY.bundles.find(b => b.available && !b.everything);
const bundledItem = bundled.items.find(id => INVENTORY.items.find(i => i.id === id).status !== 'Sold');
"""


def beacons(tmp_path, steps, *, query="", fragment="", fine=False, page="index.html"):
    """Runs steps on the page with the beacon stubbed and returns what they return."""
    setup = pointer(fine) + STUB + CLICKS
    return run_page(tmp_path, page, steps, setup=setup, query=query, fragment=fragment)


def test_a_flyer_scan_sends_one_visit_and_leaves_no_utm_in_the_address(tmp_path):
    result = beacons(
        tmp_path,
        "return { sent: BEACONS, search: location.search, hash: location.hash };",
        query=FLYER,
    )
    assert result["sent"] == [
        {"url": "/api/hit", "body": {"event": "visit", "source": "flyer", "locale": "en"}}
    ]
    assert result["search"] == ""


def test_the_spanish_page_says_so(tmp_path):
    result = beacons(tmp_path, "return BEACONS;", query="utm_source=facebook", page="es/index.html")
    assert result == [
        {"url": "/api/hit", "body": {"event": "visit", "source": "facebook", "locale": "es"}}
    ]


def test_only_the_utm_parameters_leave_the_address(tmp_path):
    result = beacons(
        tmp_path,
        "return { sent: BEACONS.map(b => b.body.event), search: location.search, hash: location.hash };",
        query="utm_source=flyer&ref=keep&utm_campaign=moving-sale",
        fragment="not-an-item",
    )
    assert result["sent"] == ["visit"]
    assert result["search"] == "?ref=keep"
    # The page's own hash handling drops the hash once it has opened (or not found) the item.
    assert result["hash"] == ""


def test_a_page_with_no_utm_sends_nothing_on_load(tmp_path):
    assert beacons(tmp_path / "plain", "await wait(100); return BEACONS;") == []
    assert beacons(tmp_path / "other", "await wait(100); return BEACONS;", query="ref=keep") == []


def test_a_reload_after_the_strip_is_not_a_second_visit(tmp_path):
    with open_page(tmp_path, "index.html", pointer(False) + STUB, query=FLYER) as browser:
        assert browser.run("return BEACONS.length;") == 1
        assert browser.run("return location.search;") == ""
        browser.send("Page.reload")
        browser.wait_for("Page.loadEventFired")
        assert (
            browser.run(
                "await until(() => document.readyState === 'complete'); return BEACONS.length;"
            )
            == 0
        )
        # The reload kept the landing source for the taps of the same tab.
        assert (
            browser.run("openModal(INVENTORY.items[0].id); return BEACONS[0].body.source;")
            == "flyer"
        )


def test_opening_an_item_is_a_view_with_the_landing_source(tmp_path):
    result = beacons(
        tmp_path,
        "openModal(INVENTORY.items[0].id); return { views: BEACONS.filter(b => b.body.event === 'view_item'), id: INVENTORY.items[0].id };",
        query="utm_source=nextdoor",
    )
    assert result["views"] == [
        {
            "url": "/api/hit",
            "body": {
                "event": "view_item",
                "item": result["id"],
                "source": "nextdoor",
                "locale": "en",
            },
        }
    ]


def test_an_unknown_item_is_not_a_view(tmp_path):
    assert beacons(tmp_path, "openModal('no-such-item'); return BEACONS;") == []


def test_a_linked_item_is_a_view_with_the_source_of_the_landing(tmp_path):
    _, _, items = page_items("index.html")
    result = beacons(
        tmp_path,
        "return BEACONS.map(b => [b.body.event, b.body.source, b.body.item || null]);",
        query="utm_source=facebook",
        fragment=items[0],
    )
    assert result == [["visit", "facebook", None], ["view_item", "facebook", items[0]]]


# Every way to text, and what each one reports

TAPS = {
    "the item button": (
        "openModal(INVENTORY.items.find(i => i.category !== 'Vehicle' && i.status !== 'Sold').id);"
        "const link = document.getElementById('modalSmsLink');",
        "item",
    ),
    "the car's button": (
        f"openModal({CAR!r}); const link = document.getElementById('modalSmsLink');",
        "item",
    ),
    "the item sheet's bundle offer": (
        IN_A_BUNDLE + "openModal(bundledItem); const link = document.getElementById('upsellLink');",
        "bundle",
    ),
    "the bundle button": (
        IN_A_BUNDLE + "openSheet(document.getElementById('sheet-' + bundled.id));"
        'const link = document.querySelector(`[data-bundle-sheet="${bundled.id}"] a[data-sms-intent]`);',
        "bundle",
    ),
    "the sticky text me": (
        "const link = document.querySelector('[data-sms-role=\"sticky-text\"]');",
        None,
    ),
}


@pytest.mark.parametrize("name", TAPS)
@pytest.mark.parametrize("source", ["flyer", None])
def test_each_way_to_text_reports_one_tap_and_keeps_its_link(tmp_path, name, source):
    setup, kind = TAPS[name]
    result = beacons(
        tmp_path,
        f"""
{setup}
const views = BEACONS.length;
const before = link.getAttribute('href');
link.click();
return {{
  taps: BEACONS.slice(views).filter(b => b.body.event === 'text_tap'),
  sent: BEACONS.length - views,
  href: [before, link.getAttribute('href')],
  cancelled: CLICKS,
  bundled: typeof bundled === 'undefined' ? null : bundled.id,
  item: typeof bundledItem === 'undefined' ? null : bundledItem,
  open: (document.getElementById('itemSheet').open && document.getElementById('modalTitle').textContent) || null,
  shown: INVENTORY.items.find(i => i.title === document.getElementById('modalTitle').textContent)?.id ?? null,
}};
""",
        query=f"utm_source={source}" if source else "",
    )
    assert result["sent"] == 1, result
    (tap,) = result["taps"]
    assert tap["url"] == "/api/hit"
    body = tap["body"]
    assert body["source"] == (source or "direct")
    assert body["locale"] == "en"
    assert set(body) <= {"event", "source", "locale", "item", "bundle"}
    if kind == "bundle":
        assert body["bundle"] == result["bundled"]
        assert "item" not in body
    elif kind == "item":
        assert body["item"] == result["shown"]
        assert "bundle" not in body
    else:
        assert "item" not in body and "bundle" not in body
    assert result["href"][0] == result["href"][1], "the link is unchanged"
    assert result["href"][0].startswith("sms:")
    assert result["cancelled"] == [False], "the beacon must not cancel the native hand-off"


def test_a_tap_on_a_desktop_is_one_count_and_the_contact_sheets_hand_off_is_not_another(tmp_path):
    result = beacons(
        tmp_path,
        """
document.querySelector('[data-sms-role="sticky-text"]').click();
await until(() => sheets().includes('contactSheet'));
const afterTap = BEACONS.filter(b => b.body.event === 'text_tap').length;
document.getElementById('contactSms').click();
await wait(50);
return { afterTap, total: BEACONS.filter(b => b.body.event === 'text_tap').length,
  open: sheets(), cancelled: CLICKS };
""",
        fine=True,
    )
    assert result["afterTap"] == 1
    assert result["total"] == 1
    assert result["open"] == ["contactSheet"]
    # the page opened its own sheet for the first tap (it cancelled the hand-off) and let the second go
    assert result["cancelled"] == [True, False]


def test_no_payload_holds_the_phone_or_an_sms_uri(tmp_path):
    """ADR-002: the number never leaves the page, in any event, in any form.

    The page's number is the real one in CI. The comparison runs in the page and only counts come
    back, so a failing assertion can never print the number into a log."""
    result = beacons(
        tmp_path,
        IN_A_BUNDLE
        + """
openModal(INVENTORY.items[0].id);
document.getElementById('modalSmsLink').click();
document.getElementById('upsellLink').click();
document.querySelector('[data-sms-role="sticky-text"]').click();
openSheet(document.getElementById('sheet-' + bundled.id));
document.querySelector(`[data-bundle-sheet="${bundled.id}"] a[data-sms-intent]`).click();
const digits = getSellerPhone().replace(/\\D/g, '');
const texts = BEACONS.map(b => JSON.stringify(b));
return {
  sent: BEACONS.length,
  numberLength: digits.length,
  carryingTheNumber: texts.filter(t => t.replace(/\\D/g, '').includes(digits)).length,
  carryingAPiece: texts.filter(t => Object.values(_C).map(String).some(p => p.length >= 3 && t.includes(p))).length,
  carryingAUri: texts.filter(t => /sms:|tel:|body=/.test(t)).length,
  elsewhere: BEACONS.filter(b => b.url !== '/api/hit').length,
};
""",
        query=FLYER,
    )
    assert result["numberLength"] >= 7, "a real number to look for"
    assert result["sent"] >= 6
    assert result["carryingTheNumber"] == 0
    assert result["carryingAPiece"] == 0
    assert result["carryingAUri"] == 0
    assert result["elsewhere"] == 0


def test_a_page_whose_beacon_throws_still_works(tmp_path):
    """A beacon that cannot be sent (no API, an old browser, a blocker) is never an error."""
    result = run_page(
        tmp_path,
        "index.html",
        "openModal(INVENTORY.items[0].id); document.getElementById('modalSmsLink').click();"
        "return { open: sheets(), cancelled: CLICKS };",
        setup=pointer(False)
        + "navigator.sendBeacon = () => { throw new Error('blocked'); };"
        + CLICKS,
        query=FLYER,
    )
    assert result == {"open": ["itemSheet"], "cancelled": [False]}


def test_a_page_with_no_sendbeacon_still_works(tmp_path):
    result = run_page(
        tmp_path,
        "index.html",
        "openModal(INVENTORY.items[0].id); return sheets();",
        setup="Object.defineProperty(navigator, 'sendBeacon', { value: undefined });",
        query=FLYER,
    )
    assert result == ["itemSheet"]


def test_a_session_without_storage_still_reports_the_source(tmp_path):
    result = run_page(
        tmp_path,
        "index.html",
        "openModal(INVENTORY.items[0].id); return BEACONS.map(b => [b.body.event, b.body.source]);",
        setup=pointer(False)
        + STUB
        + "Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('denied'); } });",
        query="utm_source=offerup",
    )
    assert result == [["visit", "offerup"], ["view_item", "offerup"]]


# The real sendBeacon, over HTTP, under connect-src 'self'

POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src {connect}"
)


class Site(http.server.SimpleHTTPRequestHandler):
    """The built site, a recording stand-in for /api/hit and a Content-Security-Policy."""

    hits: list
    connect = "'self'"

    def end_headers(self):
        self.send_header("Content-Security-Policy", POLICY.format(connect=self.connect))
        super().end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        if self.path == "/api/hit":
            self.hits.append(body)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def site():
    def serve(connect="'self'"):
        hits = []
        handler = type("Handler", (Site,), {"hits": hits, "connect": connect})
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(handler, directory=str(PUBLIC))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}", hits

    servers = []
    yield serve
    for server in servers:
        server.shutdown()


def received(hits, count, seconds=5):
    end = time.monotonic() + seconds
    while len(hits) < count and time.monotonic() < end:
        time.sleep(0.05)
    return [json.loads(body) for body in hits]


VIOLATIONS = """
window.VIOLATIONS = [];
document.addEventListener('securitypolicyviolation', e => VIOLATIONS.push(e.violatedDirective));
"""


@pytest.mark.parametrize("prefix", ["", "/es"])
def test_a_flyer_scan_reaches_the_endpoint_under_connect_src_self(tmp_path, site, prefix):
    base, hits = site()
    result = run_page(
        tmp_path,
        None,
        "openModal(INVENTORY.items[0].id); await wait(200); return { violations: VIOLATIONS, search: location.search };",
        setup=VIOLATIONS,
        url=f"{base}{prefix}/?{FLYER}",
    )
    locale = "es" if prefix else "en"
    sent = received(hits, 2)
    assert [(e["event"], e["source"], e["locale"]) for e in sent] == [
        ("visit", "flyer", locale),
        ("view_item", "flyer", locale),
    ]
    assert result == {"violations": [], "search": ""}


def test_the_check_notices_a_beacon_to_another_origin(tmp_path, site):
    """Negative control: a policy that forbids the connection shows a violation, so the test
    above would fail for a beacon that left the origin."""
    base, hits = site(connect="'none'")
    result = run_page(
        tmp_path,
        None,
        "await wait(300); return VIOLATIONS;",
        setup=VIOLATIONS,
        url=f"{base}/?{FLYER}",
    )
    assert result == ["connect-src"]
    assert hits == []


@pytest.mark.parametrize("prefix", ["", "/es"])
def test_a_seller_tool_share_link_keeps_its_source_to_the_catalog(tmp_path, site, prefix):
    """/i/<id>/?utm_source=facebook is what the seller tool builds; the share page used to drop
    the query, so only the flyer would have read as a channel."""
    base, hits = site()
    _, _, items = page_items("index.html")
    result = run_page(
        tmp_path,
        None,
        "await until(() => sheets().length === 1, 5000); await wait(100);"
        "return { path: location.pathname, search: location.search, open: sheets(), v: VIOLATIONS };",
        setup=VIOLATIONS,
        url=f"{base}{prefix}/i/{items[0]}/?utm_source=facebook&utm_campaign=moving-sale",
    )
    sent = received(hits, 2)
    assert [(e["event"], e["source"], e.get("item")) for e in sent] == [
        ("visit", "facebook", None),
        ("view_item", "facebook", items[0]),
    ]
    assert result == {"path": f"{prefix}/", "search": "", "open": ["itemSheet"], "v": []}


class RealPolicySite(AppliesHeadersFile, MissingPath, http.server.SimpleHTTPRequestHandler):
    """The built site with the Content-Security-Policy its own `_headers` file asks Pages for
    (ADR-010), and a recording stand-in for /api/hit."""

    hits: list

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        if self.path == "/api/hit":
            self.hits.append(body)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def real_policy_site():
    servers = []

    def start():
        hits = []
        handler = type(
            "Handler",
            (RealPolicySite,),
            {"hits": hits, "headers_file": served_headers(PUBLIC)},
        )
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(handler, directory=str(PUBLIC))
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}", hits

    yield start
    for server in servers:
        server.shutdown()


def test_the_beacon_fires_under_the_sites_real_content_security_policy(tmp_path, real_policy_site):
    """A flyer scan, an item view and a text tap, with the strict policy of ADR-010 in place: the
    three events reach /api/hit, and the policy blocks nothing and the console logs no error."""
    base, hits = real_policy_site()
    with open_page(tmp_path, None, setup=CSP_SETUP + CLICKS, url=f"{base}/?{FLYER}") as browser:
        browser.run("openModal(INVENTORY.items[0].id); await wait(100);")
        browser.run(
            "document.querySelector('#itemSheet a[href^=\"sms:\"]').click(); await wait(100);"
        )
        sent = received(hits, 3)
        no_trouble(browser)
    assert [(e["event"], e["source"]) for e in sent] == [
        ("visit", "flyer"),
        ("view_item", "flyer"),
        ("text_tap", "flyer"),
    ]


def test_a_share_link_keeps_its_source_under_the_real_policy(tmp_path, real_policy_site):
    """The share page's redirect is the constant script the policy lists by hash (ADR-010); it
    forwards the query, so the catalog still sees the channel of a seller-tool link (ADR-011)."""
    _, _, items = page_items("index.html")
    base, hits = real_policy_site()
    url = f"{base}/i/{items[0]}/?utm_source=facebook&utm_medium=social"
    with open_page(tmp_path, None, setup=CSP_SETUP, url=url) as browser:
        browser.run("await until(() => location.pathname === '/' && sheets().length);")
        sent = received(hits, 2)
        assert browser.run("return location.search;") == ""
        no_trouble(browser)
    assert [(e["event"], e["source"], e.get("item")) for e in sent] == [
        ("visit", "facebook", None),
        ("view_item", "facebook", items[0]),
    ]
