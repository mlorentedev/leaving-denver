# Lesson 035 — `make` Fails Under BusyBox make: Keep the Makefile POSIX

**Date:** 2026-10-05
**Status:** fixed by #198 (`fix/makefile-busybox`); the guard is `test_the_makefile_uses_only_what_a_posix_make_can_parse`
**Tags:** [make, windows, busybox, ci, tooling]

## What happened

Running `make check` on this Windows machine (Git Bash) failed at parse time:

```
make: (makefile:36): expected separator
```

Line 36 was a `define tf_run` block. GNU make parses it fine (CI on ubuntu-latest
was green). The failure is that `make` on PATH resolves to **BusyBox make**
(`scoop/apps/busybox/current`), a POSIX make that has no GNU `define`/`endef`
multi-line variables. Because the whole file is parsed before any target runs,
**every** target failed there (`make help`, `make build`, ...), not only the
`infra-*` ones that used the block.

## Why it burned time

A parse error reads like a repo defect, so the instinct is to "fix the
Makefile". The check that matters is what CI runs. Verifying the tree was
innocent took a `git stash` + rebuild + re-run of a failing test subset before
touching anything.

## Root cause

GNU-only syntax in a Makefile that one machine reads with a POSIX make. Green
CI does not cover it: CI only ever runs GNU make.

## Fix

- The Terraform recipe moved out of `define tf_run` into `scripts/tf-run.sh`
  (POSIX sh, `set -eu`). Same behaviour: both secrets are read into variables
  first, a missing or empty value fails with the same message, and Terraform
  gets them in its environment only. The Makefile passes `TF_DIR`,
  `TF_TOKEN_KEY`, `SOPS_FILE` and `CF_ACCOUNT_ID` through a plain `TF_RUN`
  variable and calls `sh scripts/tf-run.sh <terraform args>`.
- Two more GNU-only constructs were replaced because a POSIX make expands them
  to nothing, silently: `$(MAKEFILE_LIST)` (the `help` target would grep stdin
  and hang) became `Makefile`, and `$(if $(ON),--on $(ON))` (also `CHANGES`,
  `DESTROY`) became the shell's `${ON:+--on "$ON"}` (`make post ON=...` would
  have dropped `--on`). A make variable given on the command line or in the
  environment reaches the recipe's environment, so the result is identical; it
  was compared before and after with `UV=echo make post ...`.
- Left as is, not known to fail (unverified without a BusyBox make): `.DEFAULT_GOAL`
  (`help` is the first target anyway), `SHELL := /bin/bash` and `.SHELLFLAGS`
  (under a POSIX make recipes run in `sh` without `pipefail`; the one pipeline
  that relied on it, `terraform show | scripts/infra-plan-guard.py`, still fails
  closed because the guard rejects empty input), `?=`, `:=`, `=`.

## Verification

BusyBox make is `pdpmake` (rmyorston/pdpmake, the POSIX make that BusyBox for
Windows ships as `make`). The BusyBox binary on the Linux dev machine was not
used (the agent harness refused to run `busybox`); instead pdpmake `master` was
built from source in a scratch directory and run against the files:

- the Makefile before this fix: `make: (Makefile.old:36): expected separator`,
  the symptom in #198, reproduced;
- the Makefile after: `make -n help`, `make -n check` and `make -n infra-plan`
  expand and exit 0; `make UV=echo post ID=x CHANNEL=f ON=2026-10-01` prints
  `--on 2026-10-01`, and without `ON` prints no `--on`;
- the old `$(MAKEFILE_LIST)` and `$(if)` forms under pdpmake expand to empty.

Not verified: the scoop BusyBox v1.38.0 binary itself (a newer pdpmake than
`master` could differ), and the test suite under pdpmake (the `make` the tests
call is whatever is on PATH). Run `make -n check` and `make help` on the Windows
machine and reopen #198 if either still fails.

## Rule

1. A Makefile construct that needs GNU make (`define`, `$(call)`, `$(eval)`,
   `$(if)`, `$(foreach)`, `$(shell)`, conditionals, `$(MAKEFILE_LIST)`,
   `.ONESHELL`) does not go in `Makefile`. Put the logic in a script under
   `scripts/` and call it from a recipe. The test above fails on any of them.
2. When a local run contradicts expectations, reproduce against a clean tree
   before blaming the diff, and check which `make` is on PATH (`make --version`).
3. A tool a second machine uses is a second consumer: CI green is not the
   same as every consumer green.

## Related

- Lesson 018: an earlier BusyBox make difference on the same machine (immediate vs
  recursive expansion of `CF_ENV`).
- #198, the tracking issue; `scripts/tf-run.sh`; `tests/test_infra_terraform.py`.
