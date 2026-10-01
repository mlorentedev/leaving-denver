"""The decommission runbook and ADR-008 (OPS-011): the end of the sale is a dated checklist
the owner follows on Nov 8 and by Nov 15, so each step has to be a command or a named
dashboard path, and no credential the repository uses can be left off the list."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = (ROOT / "docs/runbooks/decommission.md").read_text(encoding="utf-8")
ADR = next((ROOT / "docs/adr").glob("adr-008-*.md")).read_text(encoding="utf-8")
OPS = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")
WORKFLOWS = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / ".github/workflows").glob("*"))


def section(heading):
    found = re.search(rf"^## {re.escape(heading)}.*?(?=^## |\Z)", RUNBOOK, re.M | re.S)
    assert found, f"no section {heading!r}"
    return found.group(0)


def test_there_is_a_section_for_each_date():
    assert section("Nov 8")
    assert section("By Nov 15")


def test_nov_8_flips_the_switch_and_takes_the_listings_down():
    nov_8 = section("Nov 8")
    assert "sale_over: true" in nov_8
    assert "make check" in nov_8
    for channel in ("Facebook Marketplace", "Craigslist", "OfferUp", "Nextdoor", "flyer"):
        assert channel in nov_8, channel
    assert "Delete deployment" in nov_8


def test_the_end_deploy_is_rehearsed_on_a_preview_before_the_day():
    before = section("Before Nov 8")
    assert "make deploy" in before
    assert "preview.leaving-denver.pages.dev" in before
    assert "scripts/smoke.sh" in before
    assert "git checkout data/inventory.yaml" in before  # the rehearsal flip is never committed


def test_the_switch_is_flipped_before_the_secrets_go():
    # The deploy job refuses to run without SELLER_PHONE: delete it first and the deploy that
    # replaces the catalog fails.
    assert RUNBOOK.index("sale_over: true") < RUNBOOK.index("gh secret delete")


def test_every_secret_a_workflow_reads_is_deleted_in_both_environments():
    used = set(re.findall(r"secrets\.([A-Z_]+)", WORKFLOWS)) - {"GITHUB_TOKEN"}
    assert used, "no workflow secret found: the pattern is stale"
    by_nov_15 = section("By Nov 15")
    assert "gh secret delete" in by_nov_15
    assert "for environment in production preview" in by_nov_15
    for name in used | {"SELLER_SEALED"}:
        assert name in by_nov_15, f"{name} is not deleted by the runbook"


def test_by_nov_15_names_every_account_and_the_repository():
    by_nov_15 = section("By Nov 15")
    for needle in (
        "API Tokens",
        "Google Voice",
        "leaving-denver-seller",
        "bw delete item",
        "git update-ref -d refs/backup/pre-public-main",
        "gh repo archive",
    ):
        assert needle in by_nov_15, needle
    # An archived repository cannot change its secrets: archive last.
    assert by_nov_15.index("gh secret delete") < by_nov_15.index("gh repo archive")


def test_it_ends_with_a_check_that_proves_no_phone_is_served():
    done = RUNBOOK.split("### Done when")[1]
    assert "gh secret list" in done
    assert "make audit-deploy" in done
    assert "(sms|tel):" in done


def test_ops_links_the_runbook():
    assert "(decommission.md)" in OPS


def test_the_adr_keeps_the_project_and_says_why():
    assert "status: accepted" in ADR
    decision = ADR.split("## Decision")[1].split("## Consequences")[0]
    assert "The project is kept" in decision
    # The reason that settles it: a deleted pages.dev name can be claimed by anyone.
    context = ADR.split("## Context")[1].split("## Decision")[0]
    assert "first come, first served" in context
    assert "claim" in context
