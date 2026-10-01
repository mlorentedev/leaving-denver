"""
The envelope against an implementation that shares no code with seller.mjs (ADR-007 decision 4).

Every other test opens an envelope with the page's own code, so a fault in the page's key
derivation (a fixed iteration count, a wrong additional-data header) round-trips with itself and
stays green. Here node:crypto, written from the ADR, is the second opinion: it opens what the seal
wrote at exactly 1,000,000 iterations, and what it seals the page's code must open at the
iteration count the envelope names.
"""

import copy
import json

import pytest
from sealed_helpers import PASSPHRASE, open_in_node, oracle_open, oracle_seal, seal_fixture

from leaving_denver import seal

PLAINTEXT = json.dumps({"floors": {"sofa-sleeper": 7310987}, "sealed_at": "2031-05-06T07:08:09Z"})


@pytest.fixture(scope="module")
def sealed():
    envelope = json.loads(seal.seal_with_node(json.loads(PLAINTEXT), PASSPHRASE))
    return envelope


def test_the_seal_writes_exactly_one_million_iterations(sealed):
    assert sealed["iter"] == 1_000_000


def test_an_independent_implementation_opens_what_the_seal_wrote(sealed):
    assert json.loads(oracle_open(sealed)) == json.loads(PLAINTEXT)


def test_the_independent_implementation_reads_the_same_phrase_however_it_is_typed(sealed):
    assert oracle_open(sealed, PASSPHRASE.replace(" ", "-").upper()) is not None


def test_one_iteration_fewer_does_not_open(sealed):
    """The key really depends on 1,000,000: a seal that derived at another count would also
    open here at its own, but not at 999,999 under the header that says 1,000,000."""
    fewer = copy.deepcopy(sealed)
    fewer["iter"] = 999_999
    assert oracle_open(fewer) is None
    assert oracle_open(sealed) is not None


def test_a_wrong_passphrase_does_not_open_under_the_independent_implementation(sealed):
    assert oracle_open(sealed, "abacus abide abiding ability zoom") is None


@pytest.mark.parametrize("iterations", [700_000, 1_000_000])
def test_the_page_code_opens_an_envelope_sealed_independently_at_its_own_count(iterations):
    """deriveKey must use the envelope's `iter`, not a constant: 700,000 is a count the page
    never writes. A page that fixed the count would fail this and pass every round trip."""
    envelope = oracle_seal(PLAINTEXT, PASSPHRASE, iterations)
    assert json.loads(envelope)["iter"] == iterations
    assert open_in_node(envelope, PASSPHRASE) == PLAINTEXT


def test_the_page_code_rejects_an_independently_sealed_envelope_with_an_edited_count():
    envelope = json.loads(oracle_seal(PLAINTEXT, PASSPHRASE, 700_000))
    envelope["iter"] = 700_001
    assert open_in_node(envelope, PASSPHRASE) is None


def test_the_fixture_seal_also_opens_independently():
    assert oracle_open(seal_fixture()) is not None
