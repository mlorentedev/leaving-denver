---
id: "lesson-a-switch-that-retires-a-feature-retires-its-tests"
type: lesson
scope: local
tags: [testing, build, ci]
created: "2026-10-01"
source: "OPS-011 (#38): the end-of-sale build"
---

# Lesson: A Switch That Retires a Feature Retires Its Tests

## Context

`seller.sale_over: true` in `data/inventory.yaml` makes the build publish one "the sale is
over" page and no catalog. The tests were written against a catalog build: most of them read
`build/public/index.html`, or build a scratch copy of the committed data and assert on the
catalog it makes.

## Finding

With the switch on, `make check` went red: 141 failures and 27 errors, every one a test of the
catalog that now does not exist. The pull request that flips the switch runs that same gate, so
the owner's last deploy would have been blocked by the suite, with the sale already over.
Nothing in a scratch build with the switch on shows it, because those tests build the catalog
from their own data; it only appears with the switch committed.

## Guard

`tests/conftest.py` skips the catalog's tests by name while the committed switch is on, with a
reason in the report, and `test_every_test_skipped_in_end_mode_exists` fails if a listed module
or test is misspelt or gone, since a name that matches nothing skips nothing and the flip goes
red again. The decommission runbook has the owner run `make check` with the switch on before
pushing, so a catalog test added later fails there, in the PR, and joins the list.

## Amendment (2026-10-07, CI-005 #185): the manual run was not a guard

The runbook step catches a missing name only on the day someone runs it. #169, #175 and #176 had
already slipped past it once (#181–#183 listed them). Between 2026-10-03 and 2026-10-07, three
more pull requests added eight catalog tests without listing them:

- #200 added the pickup-from date to the item and bundle sheets.
- FEAT-019 (#215) added the hero Share button.
- #221 added the idle warm-up of the item sheet.

The first end-of-sale run of the full suite failed 12 test cases. A hand-kept registry is only as current as
the run that reads it, so that run now happens on every pull request: the `test-end-of-sale`
job in `.github/workflows/ci.yml` flips the switch in the runner's checkout, proves the switch
took, and runs `make test`. Deploy needs it, because a red end-of-sale run means the end deploy
fails on the day. The runbook step stays, as a rehearsal of the real flip, not as the check.
