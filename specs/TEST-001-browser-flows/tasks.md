---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - TEST-001-browser-flows

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch created from main: `test/browser-flows`
- [x] `proposal.md` is complete and acceptance criteria are testable
- [x] No open questions left in `proposal.md` "Risks / open questions"

## Implementation

- [x] Extract the FEAT-002 harness to `tests/browser_harness.py`; `test_share_button_browser.py` uses it, 6 passed unchanged
- [x] [P] [AC1] Close paths: button, backdrop and drag, then a close request; found that the `close` event never fires under virtual time (lesson-017)
- [x] [AC1] Harness moved to real time over `--remote-debugging-pipe`, with `until()` polling; Escape and the backdrop become real input
- [x] [P] [AC2] [AC3] Back, and stacked contact over item
- [x] [P] [AC4] [AC5] Desktop contact (copy, refused clipboard, item message, native link), and touch keeps `sms:`
- [x] [P] [AC6] Deep link, known and unknown id
- [x] [AC7] Mutation check: 11 mutations of the built page, each turns the suite red
- [x] Reviewer findings: stage the page with its stylesheet, fds above 4, overall deadlines and Chrome's log, the load belongs to the staged page; new tests for the other sheets' ✕, reload, double open and Escape on stacked sheets; mutation check re-run with 15 mutations

## Verification

- [x] `make check` green
- [x] 8 back-to-back runs of both browser suites green
- [x] `verification.md` filled
