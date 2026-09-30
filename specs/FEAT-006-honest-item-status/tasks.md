---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-006-honest-item-status

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch `feat/honest-item-status` from main 887134c; #18 In Progress
- [x] `proposal.md` complete; price-drop display deferred behind #19

## PR 1 — statuses, builder and page

- [x] [AC1] [AC2] [AC3] [AC6] Failing builder tests `tests/test_item_status.py` (RED: 8)
- [x] [AC1] [AC2] [AC3] Status validation, sold-last order, bundle `available`, `status_label`
- [x] [AC6] `pending` / `available` commands through one `set_status` helper; `sold` reuses it
- [x] [AC3] [AC4] [AC5] Failing page tests (RED: 5)
- [x] [AC3] [AC4] [AC5] Cards, bundle cards and sheets, item sheet logic, vehicle hero, availability line
- [x] Rendered with a sold sofa and a pending monitor; screenshots and sheet logic checked in headless Chrome

## PR 2 — hide sold

- [ ] Hide-sold toggle, once real sales push available items down

## Closing

- [ ] Every acceptance criterion covered by a test and a `features.json` entry
- [ ] `verification.md` filled in
- [ ] Independent adversarial review before archive

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/FEAT-006-honest-item-status/features.json`):

```json
[
  {
    "id": "FEAT-006-honest-item-status-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
