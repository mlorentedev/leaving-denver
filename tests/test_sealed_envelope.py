"""
The sealed envelope (ADR-007 decision 4; FEAT-009 PR 2, AC6 and the Node half of AC7): the
parameters the seal writes, what changes between two seals, and that the page's own code
opens what the Node sealer wrote.
"""

import base64
import json

import pytest
from sealed_helpers import PASSPHRASE, open_in_node

from leaving_denver import seal

PAYLOAD = {"floors": {"sofa-sleeper": 173}, "sealed_at": "2031-05-06T07:08:09Z"}


@pytest.fixture(scope="module")
def envelope():
    return json.loads(seal.seal_with_node(PAYLOAD, PASSPHRASE))


def test_the_envelope_carries_the_adr_parameters(envelope):
    assert set(envelope) == {"v", "kdf", "iter", "salt", "iv", "ct"}
    assert envelope["v"] == 1
    assert envelope["kdf"] == "PBKDF2-SHA256"
    assert envelope["iter"] == 1_000_000
    assert len(base64.b64decode(envelope["salt"], validate=True)) == 16
    assert len(base64.b64decode(envelope["iv"], validate=True)) == 12


def test_two_seals_of_one_payload_differ_in_salt_iv_and_ciphertext(envelope):
    again = json.loads(seal.seal_with_node(PAYLOAD, PASSPHRASE))
    for field in ("salt", "iv", "ct"):
        assert again[field] != envelope[field], field


def test_the_page_code_opens_what_the_node_sealer_wrote(envelope):
    assert json.loads(open_in_node(envelope, PASSPHRASE)) == PAYLOAD


@pytest.mark.parametrize(
    "spelling",
    [
        PASSPHRASE.replace(" ", "-"),
        PASSPHRASE.upper(),
        "  " + PASSPHRASE.replace(" ", "  ") + " ",
        PASSPHRASE.replace(" ", " - "),
    ],
)
def test_hyphens_case_and_spacing_do_not_change_the_passphrase(envelope, spelling):
    assert open_in_node(envelope, spelling) is not None


def test_a_wrong_passphrase_opens_nothing(envelope):
    assert open_in_node(envelope, "abacus abide abiding ability zoom") is None
    assert open_in_node(envelope, "") is None


@pytest.mark.parametrize(
    "edit",
    [
        {"iter": 1_000_001},
        {"iter": 999_999},
        {"v": 2},
        {"kdf": "PBKDF2-SHA512"},
        {"salt": base64.b64encode(bytes(16)).decode()},
    ],
    ids=lambda edit: next(iter(edit)),
)
def test_a_header_that_was_edited_fails_decryption(envelope, edit):
    """The header is the additional data, so changing it fails the tag even when the key
    would not otherwise have changed (v and kdf feed no key derivation here)."""
    assert open_in_node({**envelope, **edit}, PASSPHRASE) is None


def test_a_flipped_ciphertext_byte_fails_decryption(envelope):
    raw = bytearray(base64.b64decode(envelope["ct"]))
    raw[0] ^= 1
    assert open_in_node({**envelope, "ct": base64.b64encode(raw).decode()}, PASSPHRASE) is None


def test_nothing_in_the_envelope_names_the_passphrase_or_the_payload(envelope):
    text = json.dumps(envelope)
    assert "sofa-sleeper" not in text
    assert "abacus" not in text
