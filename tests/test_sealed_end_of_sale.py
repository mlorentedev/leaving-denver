"""
The sealed private data and the end of the sale (OPS-011 with FEAT-009 PR 2, ADR-007 and ADR-008).

With `seller.sale_over: true` /seller/ is not built, so a SELLER_SEALED that is still set (the
secret is deleted after the end page is out, ADR-008) must neither reach a file nor stop the
build, and a malformed one is still refused.
"""

import copy
import json
import re

import pytest
import yaml
from sealed_helpers import PASSPHRASE, SENTINELS, seal_fixture

from leaving_denver import site_builder
from leaving_denver.config import DATA_DIR

ROOT = DATA_DIR.parent

SOURCE = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))


def inventory(over):
    data = copy.deepcopy(SOURCE)
    data["seller"]["sale_over"] = over
    return data


@pytest.fixture(scope="module")
def envelope():
    return seal_fixture()


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+13035550100")
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def everything_under(root):
    parts = []
    for path in sorted(root.rglob("*")):
        parts.append(path.relative_to(root).as_posix())
        if path.is_file():
            parts.append(path.read_bytes().decode("utf-8", errors="replace"))
    return "\n".join(parts)


def test_an_end_build_with_the_envelope_in_the_environment_emits_no_seller_page(
    scratch, monkeypatch, envelope
):
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_public_site(inventory(True))
    everything = everything_under(scratch)
    assert not (scratch / "seller").exists()
    assert "seller/" not in everything
    assert 'id="sealed"' not in everything
    assert json.loads(envelope)["ct"] not in everything
    for sentinel in SENTINELS:
        assert str(sentinel) not in everything


def test_the_same_environment_builds_the_seller_page_when_the_sale_is_on(
    scratch, monkeypatch, envelope
):
    """The test above only means something if the envelope does go in when the sale is on."""
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_public_site(inventory(False))
    page = (scratch / "seller" / "index.html").read_text(encoding="utf-8")
    assert json.loads(envelope)["ct"] in page


def test_ending_the_sale_sweeps_the_seller_page_an_earlier_build_left(
    scratch, monkeypatch, envelope
):
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_public_site(inventory(False))
    assert (scratch / "seller" / "index.html").is_file()
    site_builder.build_public_site(inventory(True))
    assert not (scratch / "seller").exists()
    assert json.loads(envelope)["ct"] not in everything_under(scratch)


def test_the_security_check_passes_an_end_build_that_has_no_seller_page(
    scratch, monkeypatch, envelope
):
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_public_site(inventory(True))
    site_builder.verify_security_guarantees()


def test_the_security_check_still_refuses_a_malformed_envelope_in_end_mode(scratch, monkeypatch):
    monkeypatch.setenv("SELLER_SEALED", '{"v":1}')
    site_builder.build_public_site(inventory(True))
    with pytest.raises(RuntimeError, match="not a valid sealed envelope"):
        site_builder.verify_security_guarantees()


def test_the_security_check_still_finds_the_envelope_anywhere_in_an_end_build(
    scratch, monkeypatch, envelope
):
    """A leak in the end build is a leak: the check must not relax because /seller/ is absent."""
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_public_site(inventory(True))
    (scratch / "index.html").write_text(
        f'<script type="application/json" id="sealed">{envelope}</script>', encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="outside /seller/"):
        site_builder.verify_security_guarantees()


def test_a_full_build_all_in_end_mode_ignores_the_envelope(
    scratch, tmp_path, monkeypatch, envelope
):
    own = tmp_path / "inventory.yaml"
    own.write_text(yaml.safe_dump(inventory(True)), encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", own)
    monkeypatch.setattr(site_builder, "build_stylesheets", lambda: None)
    monkeypatch.setenv("SELLER_SEALED", envelope)
    site_builder.build_all()
    assert not (scratch / "seller").exists()
    assert json.loads(envelope)["ct"] not in everything_under(scratch)
    assert PASSPHRASE not in everything_under(scratch)


# The runbook and the ADRs say one order, and name only commands that still exist.


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_decommission_runbook_names_no_retired_command():
    text = read("docs/runbooks/decommission.md")
    assert "leaving-denver panel" not in text
    assert "make panel" not in text
    assert "build/private" not in text


def test_the_decommission_runbook_deletes_the_sealed_secret_in_both_environments():
    text = read("docs/runbooks/decommission.md")
    loop = re.search(r"for environment in production preview; do\n\s+for name in ([^;]+); do", text)
    assert loop, "the deletion loop is gone"
    assert "SELLER_SEALED" in loop.group(1).split()
    assert "gh secret delete" in text


def test_every_command_the_runbook_tells_the_owner_to_run_is_a_make_target():
    makefile = read("Makefile")
    for target in set(re.findall(r"`make ([a-z-]+)", read("docs/runbooks/decommission.md"))):
        assert re.search(rf"^{target}:", makefile, re.M), target


def test_adr_007_follows_the_order_of_adr_008_and_the_runbook():
    adr = read("docs/adr/adr-007-private-seller-data-travels-as-ciphertext.md")
    ending = adr[adr.index("- **The sale ends**") : adr.index("## References")]
    assert "docs/runbooks/decommission.md" in ending
    assert "ADR-008" in ending
    assert ending.index("deploy the end page first") < ending.index("only then delete")
    assert "redeploy" not in ending.lower().split("only then")[0]
