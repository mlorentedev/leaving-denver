"""
/seller/ unlocking in headless Chrome (ADR-007 decision 5; FEAT-009 PR 2, AC3 and AC7).

A fixture envelope, sealed by the Node step with a throwaway passphrase, is built into a page of
its own; the page opens it with the browser's WebCrypto. A wrong passphrase shows one message
and nothing else; Lock and pagehide clear the DOM; no storage API is touched.
"""

import json

import pytest
from browser_harness import needs_chrome, run_page
from sealed_helpers import (
    PASSPHRASE,
    SENTINEL_FLOOR,
    SENTINEL_NOTE,
    SENTINEL_POSTED,
    SENTINEL_PRICE_LOG,
    SENTINEL_SALE,
    SENTINEL_TARGET,
    build_site,
    dom_forms,
    fixture_private,
    oracle_seal,
    seal_fixture,
)

from leaving_denver import site_builder

pytestmark = needs_chrome

NO_MATCH = "That passphrase does not open the private data."
SECRETS = dom_forms(
    SENTINEL_FLOOR, SENTINEL_TARGET, SENTINEL_SALE, SENTINEL_PRICE_LOG, SENTINEL_NOTE
)

# Every storage door the page could use. Each is recorded, never blocked, so a call fails the
# test whatever it asked for.
SPY = """
window.STORAGE_CALLS = [];
const note = name => function () { window.STORAGE_CALLS.push(name); };
for (const method of ['getItem', 'setItem', 'removeItem', 'clear', 'key']) {
  const real = Storage.prototype[method];
  Storage.prototype[method] = function (...args) { note(`Storage.${method}`)(); return real.apply(this, args); };
}
const realOpen = IDBFactory.prototype.open;
IDBFactory.prototype.open = function (...args) { note('indexedDB.open')(); return realOpen.apply(this, args); };
const cookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
Object.defineProperty(Document.prototype, 'cookie', { configurable: true,
  get() { note('cookie.get')(); return cookie.get.call(this); },
  set(value) { note('cookie.set')(); cookie.set.call(this, value); } });
"""

HELPERS = f"""
const $ = id => document.getElementById(id);
const SECRETS = {json.dumps(SECRETS)};
const leaked = () => SECRETS.filter(secret => document.documentElement.outerHTML.includes(secret));
const unlock = async passphrase => {{
  $('passphrase').value = passphrase;
  $('unlock').requestSubmit();
  await wait(50);
  await until(() => !$('unlock-button').disabled, 20000);
}};
const state = () => ({{
  message: $('unlock-message')?.textContent ?? null,
  views: $('private-views').childElementCount,
  formHidden: $('unlock').hidden,
  itemPrivate: $('item-private').textContent,
  leaked: leaked(),
}});
"""


@pytest.fixture(scope="module")
def sealed_dist(tmp_path_factory):
    dist = tmp_path_factory.mktemp("browser") / "public"
    patcher = pytest.MonkeyPatch()
    try:
        build_site(dist, patcher, sealed=seal_fixture())
        site_builder.build_stylesheets()
    finally:
        patcher.undo()
    return dist


def run(tmp_path, sealed_dist, steps):
    return run_page(tmp_path, "seller/index.html", HELPERS + steps, setup=SPY, public=sealed_dist)


def test_before_unlocking_the_page_holds_no_private_value(tmp_path, sealed_dist):
    result = run(tmp_path, sealed_dist, "return state();")
    assert result["views"] == 0
    assert result["leaked"] == []
    assert result["formHidden"] is False


def test_a_wrong_passphrase_shows_one_message_and_nothing_else(tmp_path, sealed_dist):
    result = run(
        tmp_path,
        sealed_dist,
        """
await unlock('abacus abide abiding ability zoom');
const after = state();
await unlock('');
return { after, text: document.body.innerText };
""",
    )
    after = result["after"]
    assert after["message"] == NO_MATCH
    assert after["views"] == 0
    assert after["leaked"] == []
    assert after["itemPrivate"] == ""
    assert after["formHidden"] is False
    assert "as of" not in result["text"]


def test_the_right_passphrase_opens_the_views_the_node_seal_wrote(tmp_path, sealed_dist):
    """AC7: the browser opens what the Node step sealed."""
    result = run(
        tmp_path,
        sealed_dist,
        f"""
await unlock({json.dumps(PASSPHRASE)});
const select = $('item');
select.value = [...select.options].find(o => o.textContent.includes('Sleeper')).value;
select.dispatchEvent(new Event('change'));
return {{ ...state(), text: $('private-views').innerText, asOf: $('as-of')?.textContent,
  due: $('due').innerText, total: $('plan-total').innerText }};
""",
    )
    assert result["message"] == ""
    assert result["formHidden"] is True
    text = result["text"]
    assert f"{SENTINEL_FLOOR:,}" in text
    assert f"{SENTINEL_TARGET:,}" in text
    assert f"{SENTINEL_SALE:,}" in text
    assert f"{SENTINEL_PRICE_LOG:,}" in text
    assert SENTINEL_NOTE in text
    assert result["asOf"].startswith("Private data as of ")
    assert "2031" in result["asOf"]
    # The floor and the note follow the item chosen in the listing tool.
    assert f"{SENTINEL_FLOOR:,}" in result["itemPrivate"]
    assert SENTINEL_NOTE in result["itemPrivate"]
    assert SENTINEL_POSTED not in result["itemPrivate"]
    assert result["total"].startswith("Total")


def test_lock_and_pagehide_clear_the_dom(tmp_path, sealed_dist):
    result = run(
        tmp_path,
        sealed_dist,
        f"""
await unlock({json.dumps(PASSPHRASE)});
const open = state();
$('lock').click();
const locked = state();
await unlock({json.dumps(PASSPHRASE)});
window.dispatchEvent(new Event('pagehide'));
return {{ open, locked, hidden: state(), field: $('passphrase').value }};
""",
    )
    assert result["open"]["views"] > 0
    assert result["open"]["leaked"] != []
    for after in (result["locked"], result["hidden"]):
        assert after["views"] == 0
        assert after["leaked"] == []
        assert after["itemPrivate"] == ""
        assert after["formHidden"] is False
    assert result["field"] == ""


def test_no_storage_api_is_touched_by_a_wrong_or_a_right_unlock(tmp_path, sealed_dist):
    result = run(
        tmp_path,
        sealed_dist,
        f"""
await unlock('abacus abide abiding ability zoom');
await unlock({json.dumps(PASSPHRASE)});
$('lock').click();
const calls = [...window.STORAGE_CALLS];
let stored = 0;
try {{ stored = localStorage.length + sessionStorage.length; }} catch {{ stored = 0; }}
return {{ calls, stored, cookie: document.cookie }};
""",
    )
    assert result["calls"] == []
    assert result["stored"] == 0
    assert result["cookie"] == ""


def test_the_storage_spy_would_notice_a_storage_call(tmp_path, sealed_dist):
    """Without this the test above could pass on a spy that never fires."""
    result = run(
        tmp_path,
        sealed_dist,
        """
try { localStorage.getItem('x'); } catch {}
try { sessionStorage.setItem('x', 'y'); } catch {}
indexedDB.open('probe');
document.cookie = 'probe=1';
return window.STORAGE_CALLS;
""",
    )
    assert {"Storage.getItem", "Storage.setItem", "indexedDB.open", "cookie.set"} <= set(result)


def test_a_build_without_the_secret_has_no_unlock_and_the_public_half_works(tmp_path):
    dist = tmp_path / "public"
    patcher = pytest.MonkeyPatch()
    try:
        build_site(dist, patcher)
        site_builder.build_stylesheets()
    finally:
        patcher.undo()
    result = run_page(
        tmp_path,
        "seller/index.html",
        """
const $ = id => document.getElementById(id);
return { unlock: Boolean($('unlock')), note: $('no-private')?.textContent,
  description: $('description').value, options: $('item').options.length };
""",
        public=dist,
    )
    assert result["unlock"] is False
    assert result["note"] == "No private data in this build."
    assert result["description"]
    assert result["options"] > 0


def test_the_browser_opens_an_envelope_sealed_independently_at_its_own_iteration_count(tmp_path):
    """The page's deriveKey must use the envelope's `iter`. The envelope is sealed by node:crypto
    at 700,000 iterations (a count the page never writes), so a page that fixed the count could
    not open it, whatever it does with its own seals."""
    from datetime import UTC, datetime

    from leaving_denver import seal

    payload = seal.allowlisted_payload(fixture_private(), datetime(2031, 5, 6, 7, 8, 9, tzinfo=UTC))
    envelope = oracle_seal(json.dumps(payload), PASSPHRASE, 700_000)
    dist = tmp_path / "public"
    patcher = pytest.MonkeyPatch()
    try:
        build_site(dist, patcher, sealed=envelope)
        site_builder.build_stylesheets()
    finally:
        patcher.undo()
    result = run_page(
        tmp_path,
        "seller/index.html",
        HELPERS
        + f"""
await unlock({json.dumps(PASSPHRASE)});
return {{ ...state(), text: $('private-views').innerText }};
""",
        public=dist,
    )
    assert result["message"] == ""
    assert result["formHidden"] is True
    assert f"{SENTINEL_FLOOR:,}" in result["text"]
