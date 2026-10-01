"""
The sealed block in the built /seller/ page (ADR-007 decisions 2, 3 and 5; FEAT-009 PR 2):

- AC1: no plaintext private value in any built file, and the envelope holds the allow-list only;
- AC2: the build fails closed without the secret and refuses a malformed envelope;
- AC8: the envelope lives in /seller/index.html and nowhere else.

The data is the fixture's with a sentinel planted in every allow-listed key.
"""

import base64
import html
import json
import re
from datetime import UTC, datetime

import pytest
from sealed_helpers import (
    PASSPHRASE,
    SENTINEL_SEALED_AT,
    SENTINELS,
    build_site,
    fixture_private,
    json_block,
    open_in_node,
)

from leaving_denver import seal

ALLOW_LIST = {"floors", "targets", "sales", "tracking", "notes", "sealed_at"}
NEVER_SEALED = ("5555550100", "cf-token-sentinel")


@pytest.fixture(scope="module")
def sealed_build(tmp_path_factory):
    private = fixture_private()
    private["cloudflare_pages_token"] = "cf-token-sentinel"
    payload = seal.allowlisted_payload(private, datetime(2031, 5, 6, 7, 8, 9, tzinfo=UTC))
    envelope = seal.seal_with_node(payload, PASSPHRASE)
    dist = tmp_path_factory.mktemp("sealed") / "public"
    patcher = pytest.MonkeyPatch()
    try:
        build_site(dist, patcher, sealed=envelope)
    finally:
        patcher.undo()
    return {"dist": dist, "envelope": json.loads(envelope), "text": envelope}


def readable_forms(text):
    """What a reader of the file could see: as written, with HTML entities decoded, and with
    JSON \\uXXXX escapes decoded."""
    unescaped = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    return [text, html.unescape(text), unescaped, html.unescape(unescaped)]


def test_no_built_file_holds_a_private_value_or_the_phone(sealed_build):
    files = [p for p in sealed_build["dist"].rglob("*") if p.is_file()]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for form in readable_forms(text):
            for secret in (*SENTINELS, *NEVER_SEALED, SENTINEL_SEALED_AT):
                assert secret not in form, f"{secret} found in {path.name}"


def test_the_envelope_opens_to_the_allow_list_and_nothing_else(sealed_build):
    payload = json.loads(open_in_node(sealed_build["envelope"], PASSPHRASE))
    assert set(payload) == ALLOW_LIST
    assert payload["sealed_at"] == "2031-05-06T07:08:09Z"
    assert payload["notes"]["sofa-sleeper"] == "sentinel-note-kestrel-4471"
    flat = json.dumps(payload)
    for secret in NEVER_SEALED:
        assert secret not in flat


def test_the_seller_page_embeds_the_validated_envelope(sealed_build):
    page = (sealed_build["dist"] / "seller" / "index.html").read_text(encoding="utf-8")
    assert json_block(page, "sealed") == sealed_build["envelope"]
    assert "No private data in this build" not in page


def test_the_envelope_is_in_the_seller_page_only(sealed_build):
    ciphertext = sealed_build["envelope"]["ct"]
    holders = [
        p.relative_to(sealed_build["dist"]).as_posix()
        for p in sealed_build["dist"].rglob("*")
        if p.is_file()
        and (
            ciphertext in p.read_text(encoding="utf-8", errors="replace")
            or 'id="sealed"' in p.read_text(encoding="utf-8", errors="replace")
        )
    ]
    assert holders == ["seller/index.html"]


def test_a_build_without_the_secret_has_no_sealed_block_and_says_so(tmp_path, monkeypatch):
    build_site(tmp_path / "public", monkeypatch)
    page = (tmp_path / "public" / "seller" / "index.html").read_text(encoding="utf-8")
    assert json_block(page, "sealed") is None
    assert 'id="sealed"' not in page
    assert "No private data in this build" in page
    assert (tmp_path / "public" / "seller" / "seller.mjs").is_file()


def test_an_empty_secret_reads_as_unset(tmp_path, monkeypatch):
    """A secret that is not set still arrives from CI as an empty string."""
    build_site(tmp_path / "public", monkeypatch, sealed="  ")
    page = (tmp_path / "public" / "seller" / "index.html").read_text(encoding="utf-8")
    assert "No private data in this build" in page


def b64(size):
    return base64.b64encode(bytes(size)).decode()


GOOD = {"v": 1, "kdf": "PBKDF2-SHA256", "iter": 1_000_000, "salt": b64(16), "iv": b64(12)}
GOOD["ct"] = b64(64)

MALFORMED = {
    "not json": "{not json",
    "not an object": "[1, 2]",
    "version 2": json.dumps({**GOOD, "v": 2}),
    "version as text": json.dumps({**GOOD, "v": "1"}),
    "other kdf": json.dumps({**GOOD, "kdf": "scrypt"}),
    "iter below the floor": json.dumps({**GOOD, "iter": 599_999}),
    "iter as text": json.dumps({**GOOD, "iter": "1000000"}),
    "iter as a bool": json.dumps({**GOOD, "iter": True}),
    "salt of 15 bytes": json.dumps({**GOOD, "salt": b64(15)}),
    "salt of 17 bytes": json.dumps({**GOOD, "salt": b64(17)}),
    "iv of 11 bytes": json.dumps({**GOOD, "iv": b64(11)}),
    "iv of 13 bytes": json.dumps({**GOOD, "iv": b64(13)}),
    "ciphertext not base64": json.dumps({**GOOD, "ct": "***"}),
    "ciphertext shorter than the tag": json.dumps({**GOOD, "ct": b64(15)}),
    "missing ciphertext": json.dumps({k: v for k, v in GOOD.items() if k != "ct"}),
    "an extra key": json.dumps({**GOOD, "note": "x"}),
}


@pytest.mark.parametrize("bad", MALFORMED.values(), ids=MALFORMED.keys())
def test_a_malformed_envelope_fails_the_build_without_echoing_it(bad, tmp_path, monkeypatch):
    with pytest.raises(RuntimeError) as failure:
        build_site(tmp_path / "public", monkeypatch, sealed=bad)
    assert "SELLER_SEALED" in str(failure.value)
    assert bad not in str(failure.value)


def test_a_well_formed_envelope_passes_the_check():
    assert seal.validate_envelope(json.dumps(GOOD)) == GOOD


def test_the_floor_is_the_owasp_one():
    assert seal.MIN_ITERATIONS == 600_000
    assert seal.validate_envelope(json.dumps({**GOOD, "iter": 600_000}))["iter"] == 600_000
