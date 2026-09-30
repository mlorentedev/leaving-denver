---
tags: [spec, tasks, templates]
created: "2026-09-29"
---

# Tasks - PERF-001-responsive-images

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch `feat/responsive-images` from main 5ef36ba (worktree `../leaving-denver-perf`)
- [x] `proposal.md` complete, acceptance criteria testable
- [x] No open questions left in "Risks / open questions"

## Implementation (PR A)

- [x] [AC1] [AC4] Failing tests: variant widths, no upscaling, no EXIF, upright output, incremental skip (RED: `VARIANT_WIDTHS` missing)
- [x] [AC1] [AC4] `image_processor`: `exif_transpose`, WebP 480/800/1200w, `is_up_to_date`
- [x] [AC2] [AC3] [AC5] Failing tests on the built EN/ES pages and `photo_set`
- [x] [AC2] `site_builder.photo_set` adds a parallel `photos` field; `images` unchanged
- [x] [AC2] [AC3] Template `photo` macro for hero, cards and bundle thumbs; dialog sets `srcset`/`sizes`
- [x] [AC5] Budget replay of the browser's choice

## Follow-up (PR B, same issue)

- [ ] Fonts: self-host one variable font or use the system stack (5 Google weights today)

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes (`make lint`)
- [x] No unrelated changes in the diff
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder (#89)

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/PERF-001-responsive-images/features.json`):

```json
[
  {
    "id": "PERF-001-responsive-images-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
