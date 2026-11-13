---
spec: "OPS-019-prune-deployments"
verdict: "PASS"
reviewed_sha: "a17a1f336cac71b0c3edd03edad7bfc6ee6b09b8"
reviewer: "agy/gemini-3.8-flash-high"
date: "2026-11-12"
---

## Adversarial review

**Scope**: OPS-019-prune-deployments (`git diff 497bd34cd84e7de643d95163bb80b18c7771caec...HEAD`, spec commit `82004af050ff`)
**Sources**:
- `specs/OPS-019-prune-deployments/{proposal,tasks,verification,features}.md`
- `scripts/prune-deployments.sh`
- `Makefile`
- `docs/runbooks/decommission.md`
- `docs/lessons/lesson-045-pages-refuses-to-delete-an-aliased-deployment-without-force.md`
- `tests/test_prune_deployments.py`
- `tests/test_decommission_runbook.py`

### Spec and task alignment

The change implements an automated, safe decommissioning tool to prune stale Cloudflare Pages deployments while preserving the live production deployment.

1. **Acceptance Criteria Verification**:
   - **AC1 (Dry run safety & listing)**: Verified. `scripts/prune-deployments.sh` lists all deployments, extracts canonical keeper, flags deletions vs keeper, issues zero HTTP DELETE requests. Tested by `tests/test_prune_deployments.py::test_a_dry_run_names_every_deployment_and_writes_nothing`.
   - **AC2 (`--apply` execution & stop-at-first-failure)**: Verified. Issues DELETE calls with `?force=true` for non-keepers, excludes keeper, aborts immediately on first API failure with status 1. Tested by `test_the_production_alias_holder_is_kept_and_the_rest_are_deleted`, `test_every_delete_asks_for_force_so_an_aliased_preview_can_go`, and `test_a_failed_delete_stops_the_run_non_zero`.
   - **AC3 (Fail-closed keeper resolution)**: Verified. When `canonical_deployment` is absent or unlisted in deployment pagination, exits non-zero without deletions even under `--apply`. Tested by `test_a_project_without_a_canonical_deployment_deletes_nothing` and `test_a_canonical_deployment_missing_from_the_list_deletes_nothing`.
   - **AC4 (Skip unsettled builds)**: Verified. Deployments in active/in-progress stages are preserved and reported as `skip`. Tested by `test_a_deployment_still_building_is_skipped_and_the_run_says_so`.
   - **AC5 (Pagination traversal)**: Verified. Pages API pagination traverses all pages (`per_page=25`). Tested by `test_pagination_is_followed`.
   - **AC6 (Credential security)**: Verified. API token arrives via environment and travels to curl via stdin config (`-K -`), never appearing in process arguments or stdout/stderr. Missing credentials refuse before network calls. Tested by `test_the_token_travels_on_stdin_and_never_on_argv` and `test_a_missing_credential_refuses_to_start`.
   - **AC7 (Makefile interface & runbook documentation)**: Verified. `make prune-deployments` (dry run) and `make prune-deployments-apply` (apply) exist, both are declared `.PHONY`, and step 4 of `docs/runbooks/decommission.md` documents both while retaining manual dashboard fallback. Tested by `test_deleting_is_its_own_target_and_no_variable_selects_it`, `test_both_targets_are_phony`, and `test_by_nov_9_flips_the_switch_and_takes_the_listings_down`.
   - **AC8 (In-progress exit code 3, settled cancellation, ambient variable isolation)**: Verified in implementation and tests (`test_a_deployment_still_building_is_skipped_and_the_run_says_so`, `test_a_canceled_deployment_is_settled_and_deleted`, `test_an_ambient_apply_does_not_turn_a_dry_run_into_a_delete`).

2. **Alignment & Traceability Discrepancies**:
   - `tasks.md` marked `[x] Every acceptance criterion has a matching entry in features.json`, but `features.json` defines features `f1` through `f6` covering AC1–AC7 without a dedicated feature entry for AC8.
   - `tasks.md` lacks a dedicated task item for `[AC8]`.
   - `proposal.md` frontmatter retains `status: implementing` and acceptance criteria checkboxes are `- [ ]`.
   - These are contract-level bookkeeping gaps that do not impair code correctness, security, or test coverage.

### Findings

| Severity | Reality | Area | Finding | Evidence | Test (named, or UNTESTED) | Fix location (code / tests / spec / vault) |
|---|---|---|---|---|---|---|
| Minor | THEORETICAL | security/tempfile | Predictable temporary file path in `/tmp` without `mktemp` (`list="${TMPDIR:-/tmp}/prune-deployments.$$"`) appends with `>>` rather than creating an exclusive, sanitized temp file | `scripts/prune-deployments.sh:82,95`; shared world-writable `/tmp` risk on multi-user systems | UNTESTED | code (`list="$(mktemp "${TMPDIR:-/tmp}/prune-deployments.XXXXXX")"`) |
| Minor | REAL | spec-alignment | AC8 was introduced into `proposal.md` during review iterations but was not registered as a feature in `features.json` or tracked as a task in `tasks.md` | `specs/OPS-019-prune-deployments/proposal.md:109` vs `features.json:1-44` and `tasks.md:20-40` | `test_a_deployment_still_building_is_skipped_and_the_run_says_so` | spec (`features.json`, `tasks.md` in follow-up) |
| Minor | REAL | spec-hygiene | `proposal.md` frontmatter status remains `implementing` and AC checkboxes remain unchecked (`- [ ]`) despite complete implementation and green tests | `specs/OPS-019-prune-deployments/proposal.md:4,98-117` | UNTESTED | spec (`proposal.md` in follow-up) |
| Minor | SPECULATIVE | resilience | `total_pages` parsing assumes integer string; malformed/non-numeric JSON value could cause bash arithmetic evaluation syntax error | `scripts/prune-deployments.sh:96-97` (`[ "$page" -lt "$total" ]`) | UNTESTED | code (fallback sanitizer in `jq`) |
| Minor | REAL | cli-output | Consecutive `---` delimiters printed when `make prune-deployments-apply` deletes 0 deployments | Observed in probe execution (`echo "---"` on line 129 and 151) | UNTESTED | code (`scripts/prune-deployments.sh`) |

### Evaluator rubric

| Dimension | Grade (A-D) | Rationale (one line) |
|---|---|---|
| Correctness | A | All 8 acceptance criteria proved with automated tests; fail-closed keeper guards and force-delete verified against real Cloudflare API. |
| Verification | A | 15 script unit/mock tests and 18 runbook tests pass (33 total); real production execution and post-run smoke evidence documented. |
| Scope | A | Diff strictly limited to script, Makefile targets, decommission runbook step, lesson-045, and test suite. |
| Reliability | B | Fail-closed keeper validation and stop-at-first-failure ensure safety; minor theoretical vulnerability in `/tmp` tempfile handling. |
| Maintainability | A | Clean shell script with `set -euo pipefail`, explicit usage, CC well below limit, and documented lesson in `docs/lessons/`. |
| Handoff-readiness | B | Runbook and operational lesson fully documented; minor tracking omissions in `features.json` and `proposal.md` metadata. |

### Verdict

**PASS (adversarial)**

No Blockers and no REAL Majors exist. All rubric dimensions meet or exceed grade B (four A, two B). The implementation is robust, fail-closed, rigorously tested against negative and boundary cases, and verified against the live environment.

### Recommended next steps

The contract set (`proposal.md`, `tasks.md`, `features.json`) is closed and MUST NOT be modified prior to archiving, as doing so would invalidate the review digests and trip the archive freshness check.

1. **Archive Readiness**: `dotf spec archive OPS-019-prune-deployments` is **advisable** in the current state.
2. **Follow-up / Verification disposition**:
   - Implementer may disposition the Minor findings (tempfile hardening with `mktemp` and double-delimiter cleanup) in `verification.md` or file a follow-up ticket for future shell scripts.
   - Proceed with standard archive workflow: `dotf spec archive OPS-019-prune-deployments --pr <url>`.
