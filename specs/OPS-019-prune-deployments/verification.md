---
tags: [spec, verification, templates]
created: "2026-11-10"
id: "OPS-019-prune-deployments"
type: spec-verification
status: active
owner: manu
---

# Verification - OPS-019-prune-deployments

## Evidence

- **AC1, AC6 — the dry run names everything and writes nothing.** `tests/test_prune_deployments.py`
  (`test_a_dry_run_names_every_deployment_and_writes_nothing`,
  `test_the_token_travels_on_stdin_and_never_on_argv`,
  `test_a_missing_credential_refuses_to_start`) run the script against a stubbed Cloudflare API
  that records every `curl` invocation: no `-X DELETE` appears, each deployment id appears once,
  the keeper is the single `keep` line, the token is in curl's stdin config and in no argument
  list, and the run stops before the API when a credential is missing.
- **AC2 — `--apply` deletes exactly the non-keepers.** `test_the_production_alias_holder_is_kept_and_the_rest_are_deleted`
  and `test_every_delete_asks_for_force_so_an_aliased_preview_can_go` (the `?force=true` shape was
  forced by the real API, below); `test_a_failed_delete_stops_the_run_non_zero` proves the first
  failure ends the run with nothing attempted after it.
- **AC3 — fail closed.** `test_a_project_without_a_canonical_deployment_deletes_nothing` and
  `test_a_canonical_deployment_missing_from_the_list_deletes_nothing`: non-zero, no DELETE, even
  with `--apply`.
- **AC4, AC5 — skip and paginate.** `test_a_deployment_still_building_is_skipped` (a `latest_stage.status`
  of `active` is never deleted) and `test_pagination_is_followed` (a second API page is covered).
- **AC7 — the target and the runbook.** `make -n prune-deployments` prints the sops substitution, not
  a token, and defaults to `--dry-run`; `tests/test_decommission_runbook.py` asserts that step 4
  names both commands and still names the dashboard path.

The run against the real project (2026-11-11), from a machine holding the sops key:

```
$ make prune-deployments           # 242 deployments, 81 pages
--- 
241 to delete, 0 skipped, 1 keep. Nothing was deleted: re-run with --apply

$ make prune-deployments APPLY=1
prune-deployments: deleting 6e2aca84-… failed after 0 deleted: the rest were left alone
curl: (22) The requested URL returned error: 400
```

That failure is the finding this spec records: the API answered
`{"code": 8000035, "message": "You cannot delete an aliased deployment without a `?force=true`
parameter in the API request URL"}` for the `candidate` deployment. The script now sends
`?force=true` on every delete, and 0 deployments were removed by the failed run, which is the
stop-at-first-failure behaviour doing its job on the first real attempt.

```
$ make prune-deployments APPLY=1
241 deleted, 0 skipped, 1 keep

$ make prune-deployments
--- 
0 to delete, 0 skipped, 1 keep. Nothing was deleted: re-run with --apply
```

Production was unaffected and the closed doors are closed:

```
$ scripts/smoke.sh https://leaving-denver.pages.dev
smoke OK (sale over): https://leaving-denver.pages.dev

$ curl -s https://leaving-denver.pages.dev/ | grep -oE '<title>[^<]*</title>'
<title>The sale is over · Moving Sale</title>

$ curl -s -o /dev/null -w '%{http_code}' https://6e2aca84.leaving-denver.pages.dev/    # was the candidate build
404
$ curl -s -o /dev/null -w '%{http_code}' https://215ed087.leaving-denver.pages.dev/    # was a preview build
404

$ GET …/pages/projects/leaving-denver/deployments
{"total": 1, "ids": ["1804ac90-0f0f-4b24-b8c8-d77c366912e6"]}
```

The keeper is unchanged across all of it: `canonical_deployment` was `1804ac90-…` before the run and
is the only deployment left after it.

## Adversarial review dispositions

CodeRabbit reviewed `3daa170` (two Majors, one Minor); PR-Agent reviewed the same head (two
findings). Each is dispositioned here, and the code carries the fix where one applied.

| Finding | Severity | Disposition |
|---|---|---|
| PR-Agent: apply mode selected from the ambient `APPLY` variable, so an unrelated exported `APPLY` deletes with no visible flag | Theoretical, but the right call | **Applied.** The script now takes the mode from `--apply` alone; the Make target maps `APPLY=1` onto the flag and rejects every other value before the token is read. Tests: `test_an_ambient_apply_does_not_turn_a_dry_run_into_a_delete` (three values), `test_the_make_target_rejects_any_apply_value_but_0_and_1`. |
| PR-Agent: `call()` discards the response body on failure, so a stop reports only `curl: (22)` | Real (diagnostics) | **Applied.** The captured body goes to stderr, so `errors[].message` — what named 8000035 on the first run — reaches the operator. Test: `test_a_failed_delete_stops_the_run_non_zero` asserts the API's message, not just the status. |
| CodeRabbit Major: a skipped deployment leaves its URL reachable while the run exits 0 | Real | **Applied.** `--apply` now exits 3 with "run this again once they have settled", and the runbook tells the operator to repeat until `0 skipped` and `0 to delete`. Test: `test_a_deployment_still_building_is_skipped_and_the_run_says_so`. |
| CodeRabbit Major: the Make target deletes on `APPLY=false` or any mistyped value | Real | **Applied.** The recipe's `case` accepts only empty/`0`/`1` (POSIX, so BusyBox make still parses it). Test: `test_the_make_target_rejects_any_apply_value_but_0_and_1`. |
| CodeRabbit Minor: the token/`--fail-with-body` handling in `call()` | Minor | **Applied** as part of the body-on-stderr change: the token still travels on curl's stdin config, and `--fail-with-body` is what keeps the error body available to print. |

A second review, on `0557787`, raised two more, both real:

| Finding | Severity | Disposition |
|---|---|---|
| PR-Agent: the ambient `APPLY` risk moved rather than left — make imports the environment, so an exported `APPLY=1` still reaches the recipe | Real | **Applied.** Deleting is a target of its own (`make prune-deployments-apply`); no variable selects it. Tests: the dry-run target stays dry with `APPLY=1` exported, and only the apply target deletes. |
| PR-Agent: a `canceled` build never settles, so `--apply` would exit 3 forever and "repeat until 0 skipped" could never be satisfied | Theoretical, real consequence | **Applied.** `success`, `failure` and `canceled` are settled; only genuinely in-progress stages are skipped. Test: `test_a_canceled_deployment_is_settled_and_deleted`. |
| PR-Agent: the runbook test's `assert "make prune-deployments" in ...` is subsumed by the `-apply` line, so deleting the dry run from the runbook left it green | Real (test quality) | **Applied.** The assertion now requires the dry run on a line of its own, and a mutation (deleting that line) turns the test red. |

One finding was **not** applied: CodeRabbit's suggestion to add a `set -e`-style guard around the
per-deployment delete is already covered — the loop's `call ... || fail` is the guard, and
`test_a_failed_delete_stops_the_run_non_zero` pins it.

## Test status

- `uv run pytest tests/test_prune_deployments.py tests/test_decommission_runbook.py -q` →
  **13 + 17 passed**.
- `make check` → **1198 passed, 298 skipped** (log in the PR body; the skipped ones are the catalog
  tests listed in `tests/conftest.py`'s `CATALOG_TESTS`, plus the browser suite).

## Closing

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/OPS-019-prune-deployments/` -> `specs/archive/OPS-019-prune-deployments/`
- [ ] Bitácora board ticket closed with the PR link (ADR-018)
