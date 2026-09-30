---
tags: [spec, tasks, templates]
created: "2026-09-29"
---

# Tasks - CI-003-auto-deploy-main

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch `ci/auto-deploy-main` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open blocking questions

## Implementation

- [x] [AC1] Write `tests/test_cd_workflow.py` asserting push/main production,
  test dependency, and no PR deployment; run `uv run pytest -q tests/test_cd_workflow.py`
  (expected FAIL on manual-only deploy).
- [x] [AC2] Extend that test for guarded manual main and preview dispatch; run it
  (expected FAIL while deploy branch selection only reads `inputs.branch`).
- [x] [AC3] Extend test for nonempty real secret, smoke and public-only output;
  run it (expected FAIL on missing secret guard).
- [x] [AC1] [AC2] [AC3] Update `.github/workflows/ci.yml` to satisfy the checks;
  run targeted pytest (expected PASS), then `make check`.
- [x] [AC4] Update `README.md` and `docs/runbooks/ops.md` for automatic CD.
- [x] [AC5] Add a failing `tests/test_cd_workflow.py` case for deployment-scoped
  token and main-only branch policy; implement `.github/deployment-environment.json`
  and `Makefile` setup, then verify both GitHub environments and token scopes.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered
- [x] Every acceptance criterion has a matching entry in `features.json` (see below) with a non-vacuous verification command
- [x] Type checks pass (no typed code changed; workflow YAML parsed by tests)
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/CI-003-auto-deploy-main/features.json`):

```json
[
  {
    "id": "CI-003-auto-deploy-main-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
