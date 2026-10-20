# Lesson 042 — A Deadline Exception Belongs in the Automation, Not in the Instruction

**Date:** 2026-10-19
**Tags:** [runbook, close-out, deadlines, inventory, testing]

## What happened

The household close-out (`docs/runbooks/decommission.md`) hid every household item that was not
Sold. The office chair became the one exception (owner, 2026-10-19): it stays for sale one day
past the deadline because it may be handed over on Oct 24.

The runbook already had an escape hatch for exactly this: "an item with a pickup still to come is
`Pending`; finish that pickup first, or leave the item out of this step by hand". That is a
sentence, and a sentence is not a mechanism: the owner reads it on the day, edits a Python list in
a heredoc, and the page goes out either way. Nothing fails if it is skipped, and nothing proves it
was applied.

## Why it matters

A checklist step whose correctness lives in the operator's memory is a step that fails exactly
once — and the failure is public, because it removes a listing that is still for sale, one day
before its agreed handover. The written exception also decays: the chair id is not mentioned
anywhere the code can see it, so no test can notice when the exception is dropped, when the id
stops existing, or when the chair finally sells.

## Rule

- When one item is exempt from an automated step, put the exemption in the automation as a named,
  dated constant (`KEEP = {"office-chair-ergonomic"}` in the close-out snippet) — not in prose
  above it. The snippet then does the right thing without the operator remembering anything.
- Give the exemption an end. The rule that removes it is a step with its own date (Oct 24: the
  same snippet with `KEEP = set()`), so the exception cannot outlive its reason.
- Hold the constant to reality with a test: one asserts the snippet's ids equal the ones the test
  pins, one asserts the pinned item survives the close-out, and one asserts the state after the
  pin is emptied. A stale pin then fails the suite instead of hiding a sale.
- Check what the exception does to the page's derived facts. Keeping the chair published keeps the
  hero line, the page title and the flyer talking about furniture: the "page now sells only the
  car" claim moves to the day the last item actually goes, and the checks move with it.
