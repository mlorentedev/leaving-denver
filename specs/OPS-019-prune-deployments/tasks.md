---
tags: [spec, tasks, templates]
created: "2026-11-10"
id: "OPS-019-prune-deployments"
type: spec-tasks
status: active
owner: manu
---

# Tasks - OPS-019-prune-deployments

## Setup

- [x] Branch created from main: `feat/prune-deployments` (worktree `worktrees/leaving-denver/feat-prune-deployments`)
- [x] `proposal.md` is complete and acceptance criteria are testable
- [x] No open questions left in `proposal.md` "Risks / open questions"

## Implementation

- [x] [P] [AC1][AC6] Failing test: `tests/test_prune_deployments.py` stubs `curl` and asserts the dry
      run names every deployment once, marks the alias holder `keep`, issues no DELETE, and that the
      token travels on curl's stdin config, never in argv
- [x] [AC1] `scripts/prune-deployments.sh`: list through the API (curl `-K -`, `--fail-with-body`),
      parse with `jq`, print `keep`/`delete`/`skip` lines and the counts
- [x] [P] [AC2] Failing test: `--apply` issues one DELETE per non-keeper, none for the keeper, and a
      failed delete exits non-zero
- [x] [AC2] Implement the `--apply` path, stopping at the first failed delete
- [x] [P] [AC3] Failing test: no canonical deployment, or one absent from the list, exits
      non-zero and issues no DELETE
- [x] [AC3] Implement the fail-closed keeper check on the project's `canonical_deployment`
- [x] [P] [AC4] Failing test: a deployment whose build has not settled is skipped, not deleted
- [x] [AC4] Implement the in-progress skip
- [x] [P] [AC5] Failing test: a project spanning two API pages is fully covered
- [x] [AC5] Implement pagination
- [x] [AC6] Implement the missing-env refusal and the "token never on argv" shape
- [x] [AC7] `make prune-deployments` target (dry run by default, `APPLY=1` deletes) using the same
      `$(CF_ENV)` token plumbing as `make deploy`
- [x] [AC7] `docs/runbooks/decommission.md` step 4 names the target and keeps the dashboard fallback;
      `tests/test_decommission_runbook.py` keeps both assertions

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] `make check` green
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in with the dry run's real output
- [x] PR opened referencing this spec folder
