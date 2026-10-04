"""The decommission runbook and ADR-008 (OPS-011): the end of the sale is a dated checklist
the owner follows on Oct 23, by Nov 9 and by Nov 15, so each step has to be a command or a named
dashboard path, and no credential the repository uses can be left off the list."""

import re
from pathlib import Path

import yaml

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
    assert section("Oct 23")
    assert section("By Nov 9")
    assert section("By Nov 15")


def test_by_nov_9_flips_the_switch_and_takes_the_listings_down():
    by_nov_9 = section("By Nov 9")
    assert "sale_over: true" in by_nov_9
    assert "make check" in by_nov_9
    for channel in ("Facebook Marketplace", "Craigslist", "OfferUp", "Nextdoor", "flyer"):
        assert channel in by_nov_9, channel
    assert "Delete deployment" in by_nov_9


def test_the_end_deploy_is_rehearsed_on_a_preview_before_the_day():
    before = section("Before Nov 9")
    assert "make deploy BRANCH=preview" in before  # never the default-dependent bare target
    assert "preview.leaving-denver.pages.dev" in before
    assert "scripts/smoke.sh" in before
    assert "git checkout data/inventory.yaml" in before  # the rehearsal flip is never committed


def test_the_switch_is_flipped_before_the_secrets_go():
    # The deploy job refuses to run without SELLER_PHONE: delete it first and the deploy that
    # replaces the catalog fails. The rehearsal flips the switch too, so the order is read from
    # the dated sections: the flip in By Nov 9, the deletion in By Nov 15, and By Nov 9 comes first.
    assert "sale_over: true" in section("By Nov 9")
    assert "gh secret delete" in section("By Nov 15")
    assert "gh secret delete" not in section("By Nov 9")
    assert "gh secret delete" not in section("Before Nov 9")
    assert RUNBOOK.index("\n## By Nov 9") < RUNBOOK.index("\n## By Nov 15")


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
        "work phone",
        "leaving-denver-seller",
        "bw delete item",
        "SELLER_PASSPHRASE",
        "dotfiles",
        "git update-ref -d refs/backup/pre-public-main",
        "gh repo archive",
    ):
        assert needle in by_nov_15, needle
    # An archived repository cannot change its secrets: archive last.
    assert by_nov_15.index("gh secret delete") < by_nov_15.index("gh repo archive")


def test_no_google_voice_number_is_left_to_release():
    """The listing number is the owner's work phone (#29 closed as not planned): no runbook step
    may send the owner to release a number that does not exist."""
    for name in ("decommission.md", "ops.md", "seller-playbook.md"):
        text = (ROOT / "docs/runbooks" / name).read_text(encoding="utf-8")
        assert "Release the Google Voice" not in text, name
        assert "get a Google Voice" not in text, name


def test_the_oct_23_check_matches_the_page_the_build_makes():
    """The close-out check greps the live page for what the locale file renders (FEAT-014: no
    date is ever shown), so a reworded page fails here, not on the day."""
    oct_23 = " ".join(section("Oct 23").split())
    en = yaml.safe_load((ROOT / "locales/en.yaml").read_text(encoding="utf-8"))
    assert en["page_title_vehicle"] in oct_23
    assert en["sale_status"] in oct_23
    assert "Car available until" not in oct_23
    assert "counts down" not in oct_23


def test_by_nov_9_takes_down_the_cars_listing_and_the_reminder_workflow():
    by_nov_9 = section("By Nov 9")
    assert "Cars.com" in by_nov_9
    assert "Craigslist 48h Bump Reminder" in by_nov_9
    assert "Uptime Kuma" in by_nov_9
    assert by_nov_9.index("Uptime Kuma") < by_nov_9.index("Craigslist 48h Bump Reminder")


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


def test_no_runbook_command_prints_a_secret():
    """`bw unlock` prints the session key and `bw list items` the decrypted item JSON, which
    holds SELLER_PASSPHRASE. Each must be captured or reduced to ids before it reaches the
    terminal (PR #148 review)."""
    for line in RUNBOOK.splitlines():
        command = line.split("#", 1)[0]
        if re.search(r"\bbw unlock\b", command):
            assert "--raw" in command and "$(" in command, line
        if re.search(r"\bbw (list|get) items?\b", command):
            assert "| jq -r" in command and ".id" in command, line


def test_the_household_closeout_comes_first_and_does_not_end_the_sale():
    oct_23 = section("Oct 23")
    assert RUNBOOK.index("\n## Oct 23") < RUNBOOK.index("\n## Before Nov 9")
    assert "published: false" in oct_23
    assert "sale_over" not in oct_23
    assert "without being marked Sold" in " ".join(oct_23.split())


def test_the_sale_is_turned_off_with_the_car_not_on_a_fixed_day():
    by_nov_9 = " ".join(section("By Nov 9").split())
    assert "as soon as the car is handed over" in by_nov_9
    assert "no later than Nov 9" in by_nov_9


def test_the_terraform_objects_go_before_the_token_that_removes_them_and_the_state_goes_last():
    """ADR-012: the Access objects are destroyed with the Terraform token, so that token is
    revoked after; the n8n digest's token is not in Terraform, and the state holds the email."""
    by_nov_15 = section("By Nov 15")
    assert by_nov_15.index("make infra-apply") < by_nov_15.index("Terraform token")
    assert "3 to destroy" in by_nov_15 and "never the Pages project" in by_nov_15
    assert "leaving-denver-analytics-read" in by_nov_15 and "not in Terraform" in by_nov_15
    assert "terraform.tfstate*" in by_nov_15 and "owner_email" in by_nov_15
    assert by_nov_15.index("Terraform token") < by_nov_15.index("terraform.tfstate*")
