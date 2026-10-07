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
- The other GNU-only constructs a POSIX make may reject were replaced the same
  way, as a precaution (only `define` is known to have failed): `$(MAKEFILE_LIST)` became `Makefile`, and
  `$(if $(ON),--on $(ON))` (also `CHANGES`, `DESTROY`) became the shell's
  `${ON:+--on "$ON"}`. A make variable given on the command line or in the
  environment reaches the recipe's environment, so the result is identical; it
  was compared before and after with `UV=echo make post ...`.
- Left as is, not known to fail (unverified without a BusyBox make): `.DEFAULT_GOAL`
  (`help` is the first target anyway), `SHELL := /bin/bash` and `.SHELLFLAGS`
  (under a POSIX make recipes run in `sh` without `pipefail`; the one pipeline
  that relied on it, `terraform show | scripts/infra-plan-guard.py`, still fails
  closed because the guard rejects empty input), `?=`, `:=`, `=`.

## Not verified

BusyBox make itself was never run for this fix: the Linux `busybox` here has no
`make` applet and Debian/upstream BusyBox does not ship one (the Windows build
is a separate fork). The parse-time claim rests on the construct list above, not
on a run. Whoever has the Windows machine: run `make -n check` and `make help`
there and reopen #198 if either still fails.

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
