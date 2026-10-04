#!/usr/bin/env python3
"""Read `terraform show -json <plan>` on stdin and decide whether `make infra-apply` may go on.

Prints addresses and actions only, never a value: the plan holds the owner's email.

- An import-only plan passes: every change is a no-op, or an update whose before and after are
  identical and which has nothing unknown until apply. That is a change in sensitivity marking
  only (the sensitive owner_email marks a whole list), which Terraform words "The value is
  unchanged". The owner's first real plan showed exactly that on the policy.
- A create or an update with a real difference passes only with --allow-changes
  (`make infra-apply CHANGES=1`).
- A plan that only deletes passes only with --allow-destroy (`make infra-apply DESTROY=1`, the
  decommission runbook's switch). Nothing else lets a delete through, and a replacement (delete
  and create) never passes: a replaced Access application has a new audience and closes /seller/
  until ACCESS_AUD is set again.

- Deleting the Pages project never passes, with any switch (ADR-008).

Exit 0 to go on, 1 to refuse, 2 for input it cannot read (which refuses too).
"""

import json
import sys

QUIET = (["no-op"], ["read"])
PAGES_PROJECT = "cloudflare_pages_project."


def has_unknown(value) -> bool:
    if isinstance(value, dict):
        return any(has_unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(has_unknown(v) for v in value)
    return value is True


def is_quiet(change: dict) -> bool:
    if change["actions"] in QUIET:
        return True
    # Identical values (so only the `*_sensitive` markings differ) and nothing computed later.
    return (
        change["actions"] == ["update"]
        and "before" in change
        and "after" in change
        and change["before"] == change["after"]
        and not has_unknown(change.get("after_unknown"))
    )


def main(argv: list[str]) -> int:
    allow_changes = "--allow-changes" in argv
    allow_destroy = "--allow-destroy" in argv
    try:
        changes = json.load(sys.stdin)["resource_changes"]
        pending = [
            (change["address"], change["change"]["actions"])
            for change in changes
            if not is_quiet(change["change"])
        ]
    except (ValueError, KeyError, TypeError):
        print("infra-apply: could not read the saved plan (terraform show -json)", file=sys.stderr)
        return 2

    for address, actions in pending:
        print(f"infra-apply: {address} would {'+'.join(actions)}", file=sys.stderr)
    kept = [a for a, actions in pending if "delete" in actions and PAGES_PROJECT in a]
    if kept:
        print(
            f"infra-apply: refusing: the plan would delete {', '.join(kept)}. ADR-008 keeps the "
            "Pages project: a deleted pages.dev name can be claimed by anyone. No switch allows "
            "it here; this does not rest on prevent_destroy, which an edit of main.tf removes.",
            file=sys.stderr,
        )
        return 1
    replaced = [a for _, a in pending if "delete" in a and len(a) > 1]
    only_deletes = pending and all(a == ["delete"] for _, a in pending)
    if replaced or (
        any("delete" in a for _, a in pending) and not (only_deletes and allow_destroy)
    ):
        print(
            "infra-apply: refusing: the plan would destroy or replace something. A replaced "
            "Access application closes /seller/ until ACCESS_AUD is set again. CHANGES=1 does not "
            "allow it; a plan that only deletes, on purpose, needs DESTROY=1 "
            "(docs/runbooks/decommission.md).",
            file=sys.stderr,
        )
        return 1
    if pending and not (allow_changes or (only_deletes and allow_destroy)):
        print(
            "infra-apply: refusing: the plan changes something. If that is intended (not the "
            "first import), read it with make infra-plan and run make infra-apply CHANGES=1.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
