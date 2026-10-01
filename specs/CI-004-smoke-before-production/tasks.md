---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - CI-004-smoke-before-production

> TDD order. One task = one focused commit. Tick as you go. Reorder freely while spec is in `draft` state; freeze once you start `implementing`.
>
> **Inline markers** (optional, additive — borrowed from `github/spec-kit`, adapt-not-adopt per #141):
> - `[P]` — this task has **no dependency on another unchecked task**, so it is safe to run in parallel (fan out to a `Workflow`, or just batch). TDD chains (test → implement → refactor of the *same* behavior) are sequential and must NOT carry `[P]`; independent behaviors can.
> - `[AC<n>]` — this task helps satisfy **acceptance criterion #`<n>`** from `proposal.md`. Lets `/spec check` map coverage deterministically; omit it and the check falls back to semantic judgment.

## Setup

- [x] Branch created from main: `ci/smoke-before-production`
- [x] `proposal.md` is complete and acceptance criteria are testable
- [x] No open questions left in `proposal.md` "Risks / open questions" (the token's reach is checked by the PR run itself)

## Implementation

- [x] [P] [AC1] [AC2] Test the deploy step order (candidate deploy, candidate smoke, production deploy, canonical smoke), then rewrite the deploy steps
- [x] [P] [AC6] Test that the gate refuses the placeholder, then extend the "Require production contact" step
- [x] [P] [AC3] Test that `ci-secrets` sets `SELLER_PHONE` per environment before deleting the repo-level one, then change the Makefile
- [x] [P] [AC4] Test that every `uses:` is pinned to a SHA with a version comment, then pin them (SHAs resolved from the tags with `gh api`)
- [x] [P] [AC5] Test `scripts/audit-deploy.sh` against a stubbed `gh`, then write it, `make audit-deploy` and the weekly workflow
- [x] [AC7] Fix the Deploy step numbering and describe the candidate step in `docs/runbooks/ops.md`

## Closing

- [ ] Every acceptance criterion from `proposal.md` is covered by at least one test
- [ ] Every acceptance criterion has a matching entry in `features.json` (see below) with a non-vacuous verification command
- [ ] Type checks pass
- [ ] Lint passes
- [ ] No unrelated changes in the diff (no scope creep)
- [ ] `verification.md` filled in
- [ ] PR opened referencing this spec folder

## Machine-readable features

This spec emits a sibling `features.json` (alongside this file) following [[pattern-feature-list-as-primitive]]. The JSON is the harness-facing contract: each acceptance criterion maps to ≥1 feature with `id`, `behavior`, `verification` (executable command), `state` (lifecycle), and `evidence` (harness-captured output).

**Pass-state gating:** the agent CANNOT write `"state": "passing"` — only the harness, after running `verification` and capturing exit code 0, may set that terminal state. Reviewers must reject PRs where features.json contains `passing` entries with empty `evidence`.

Minimal `features.json` skeleton (drop into `<repo>/specs/CI-004-smoke-before-production/features.json`):

```json
[
  {
    "id": "CI-004-smoke-before-production-f1",
    "behavior": "<one-line copy of an acceptance criterion>",
    "verification": "<single shell command; exit 0 means pass>",
    "state": "pending",
    "evidence": ""
  }
]
```
