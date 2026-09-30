---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-003-accessible-catalog

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch `fix/readable-contrast` from main be55485; issue #15 In Progress
- [x] `proposal.md` complete; PR 3 channels are an open owner question

## PR 1 — readable text

- [x] [AC1] Failing test `tests/test_readable_text.py` (RED: 5 utilities on 18 lines)
- [x] [AC1] neutral-400→500, emerald-600→700, 10/11 px→`text-xs`; decorative "/" `aria-hidden`
- [x] Bundle offer still one line at 12 px (measured, see proposal risks)

## PR 2 — dialogs

- [x] [AC2] [AC3] Failing tests `tests/test_native_dialogs.py` (RED: 5)
- [x] [AC2] [AC3] `<dialog>` for item and bundle sheets, scroll lock, focus return, Back closes
- [x] Behaviour driven in headless Chrome over CDP (real clicks/Escape/history navigation) on the preview

## PR 3 — desktop contact

- [x] Owner chose show-and-copy (2026-09-30)
- [x] [AC4] Failing tests `tests/test_desktop_contact.py` (RED: 6)
- [x] [AC4] `contactSheet` dialog, fine-pointer click interception, Copy with selection fallback; Back closes one sheet level at a time
- [x] Behaviour driven over CDP (desktop via `matchMedia` stub, mobile via touch emulation); lesson-014

## Closing

- [ ] Every acceptance criterion covered by a test and a `features.json` entry
- [ ] `verification.md` filled in
- [ ] Independent adversarial review before archive

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/FEAT-003-accessible-catalog/features.json`):

```json
[
  {
    "id": "FEAT-003-accessible-catalog-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
