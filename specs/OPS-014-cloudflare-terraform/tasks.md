---
tags: [spec, tasks]
created: "2026-10-03"
---

# Tasks - OPS-014-cloudflare-terraform

> TDD order. One task = one focused commit. Tick as you go.

## Setup

- [x] Worktree and branch `feat/cloudflare-terraform` from main
- [x] `proposal.md` states testable acceptance criteria
- [x] No open questions left in `proposal.md`

## Implementation

- [x] [AC1] `tests/test_infra_terraform.py`: scanner for emails and tokens, gitignore patterns (expected FAIL before `.gitignore`).
- [x] [AC5] Module: Pages project, Access provider, policy and application, imports, outputs; provider schema read from the pinned version.
- [x] [AC7] Read-only plan of the Pages project with the deploy token.
- [x] [AC2] [AC3] [AC4] Makefile targets and their tests against stubbed `sops` and `terraform`.
- [x] [AC6] `scripts/infra-ids.sh` and its tests against a stubbed API.
- [x] CI: `hashicorp/setup-terraform` pinned by commit.
- [x] [AC8] ADR-012, ADR-005 and ADR-007 notes, ops and decommission runbooks, README, architecture, lesson-030.

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test or command
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder
