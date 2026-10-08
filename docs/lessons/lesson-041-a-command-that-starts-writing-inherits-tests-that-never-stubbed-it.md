# Lesson 041 — A Command That Starts Writing Inherits Tests That Never Stubbed It

**Date:** 2026-10-08
**Tags:** [testing, cli, inventory, fixtures, sops]

## What happened

`make reprice` used to record a price only in the private log. #236 made it also set the price in
`data/inventory.yaml`. The new tests ran against a copy of the inventory and passed. But
`tests/test_update_offer.py` had driven `cmd_reprice` for months with only the recorder stubbed,
because there was nothing else to stub. After the change, one of those old tests rewrote the
**real** sofa price (220 → 190) in the worktree and then failed for an unrelated reason (the build
had no phone number). The new tests could not have caught this: the file they protect is a copy.

The full run caught a second fixture problem. `test_the_real_sops_accepts_the_values_and_keeps_the_history`
recorded the date 2026-10-08 and then asserted that string was absent from the encrypted file.
sops writes `lastmodified` in clear text, so the assertion was false exactly on the day the
suite ran in UTC on 2026-10-08. It failed on `main` too.

## Why it matters

A test stubs what its command does on the day the test is written. When the command gains a
side effect, every older caller runs it unstubbed. Each such test is a write to the owner's real
data waiting to happen. Per-test discipline does not scale: the author of the change has to know
about every caller, in every file.

A date in a fixture is a value the system also produces. A fixture that uses "a recent date" can
collide with the real clock.

## Rule

- Guard a file the owner edits by hand at the **suite** level, not in the tests that mean to
  edit it. `tests/conftest.py::never_change_the_owners_inventory` snapshots `data/inventory.yaml`
  around every test, restores it, and fails the test that changed it. It works the same way as the
  existing guard for `data/private.sops.yaml`.
- When a command gains a write, grep for every caller in the tests (`cmd_reprice` appeared in three
  files) and stub the new write in each.
- Pick fixture dates the system cannot produce, such as 2001, when the test asserts their
  absence from output that carries timestamps.

## Related

- lesson-037 (tests that assume an item's status)
- #205, #218 (one-line inventory edits), #220 (check first, record second)
