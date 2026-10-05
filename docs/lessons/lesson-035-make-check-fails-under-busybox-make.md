# Lesson 035 — `make check` Fails Under BusyBox make: Run the Parts or Trust CI

**Date:** 2026-10-05
**Tags:** [make, windows, busybox, ci, tooling]

## What happened

Running `make check` on this Windows machine (Git Bash) failed at parse time:

```
make: (makefile:36): expected separator
```

Line 36 is a `define tf_run` block. The Makefile is correct — GNU make parses it
fine (CI on ubuntu-latest is green). The failure is that `make` on PATH resolves
to **BusyBox make** (`scoop/apps/busybox/current`), whose `make` does not support
GNU `define`/`endef` multi-line variables the same way.

## Why it burned time

A parse error reads like a repo defect, so the instinct is to "fix the
Makefile". The check that matters is what CI runs. Verifying the tree was
innocent took a `git stash` + rebuild + re-run of a failing test subset before
touching anything.

## Root cause

`define`/`endef` recipe blocks (and other GNU extensions) in `Makefile` +
BusyBox make on the local PATH. Environmental, not repo breakage.

## Rule

1. On this machine, do not treat `make check` output as repo truth. Run the
   parts directly: `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run leaving-denver build`, `uv run pytest`.
2. When a local run contradicts expectations, reproduce against a clean tree
   (`git stash` → run → `git stash pop`) before blaming the diff.
3. CI (ubuntu, GNU make) is the authoritative gate for `make check`.

## Related

- Ticketed: the local-dev breakage tracking issue (see bitácora, 2026-10-05).
