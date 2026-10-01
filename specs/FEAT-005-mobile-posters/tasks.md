---
tags: [spec, tasks, templates]
created: "2026-09-29"
---

# Tasks - FEAT-005-mobile-posters

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch `feat/mobile-posters` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] Access configuration is a deployment prerequisite, not a code ambiguity

## Implementation

- [x] [AC1] [AC3] Write `tests/test_mobile_poster.py` asserting built
  `/seller/index.html` contains only sanitized, published items and no PIN;
  run `uv run pytest -q tests/test_mobile_poster.py` (expected FAIL: file absent).
- [x] [AC1] Write Node assertions for listing copy, price and UTM-attributed
  item links from `src/leaving_denver/assets/seller.mjs`.
- [x] [AC1] [AC3] Add `src/leaving_denver/templates/seller.html`, seller JS,
  `src/leaving_denver/site_builder.py` output, and Tailwind source; re-run
  targeted tests (expected PASS).
- [x] [AC2] Write a failing missing-config/invalid-token test for
  `functions/_middleware.js`; pin Access plugin with npm, implement
  root Pages middleware protecting all seller assets, run targeted tests.
- [x] [AC4] Document exact owner-only Access setup, aliases and smoke gate in
  `docs/runbooks/ops.md` and `README.md`. Run `make check`.
- [x] [AC2] [AC4] Configure Access application and Pages variables on Cloudflare
  once authorized; verify anonymous denial and owner login on production and
  preview before advertising the URL. Do not publish private workspace.
  Done 2026-09-30 by the owner. The Access app covers `seller` and `seller/*` on
  `leaving-denver.pages.dev` and `*.leaving-denver.pages.dev`, allowing One-time PIN
  for the owner's email only. `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` are set for
  Production and Preview. Anonymous `/seller`, `/seller/`, `/seller/index.html` and
  `/seller/seller.mjs` return 302 to `mlorentedev.cloudflareaccess.com` on
  production and on `candidate.leaving-denver.pages.dev`, while `/` stays 200. The
  owner signed in on a phone and a computer and the tool works. Still open: the
  unlisted-identity denial check (owner).

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json` (see below) with a non-vacuous verification command
- [x] Type checks pass (Python lint and JS module syntax/Pages Functions build)
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [ ] PR opened referencing this spec folder

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/FEAT-005-mobile-posters/features.json`):

```json
[
  {
    "id": "FEAT-005-mobile-posters-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
