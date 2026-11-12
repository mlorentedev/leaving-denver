---
spec: "OPS-018-close-out"
verdict: "PASS-WITH-GAPS"
reviewed_sha: "5bc70f9ea721a1f5f2c919585a2308671e1bf6d6"
reviewer: "nan/glm5.3-flash"
date: "2026-11-10"
---

## Adversarial review

**Scope**: OPS-018-close-out (PRs #268 and #269, merged)
**Sources**: `specs/OPS-018-close-out/{proposal,tasks,verification,features.json}`; `git diff 8972c892462ccc477a0052aaa21930c29c124ce3...HEAD` (branch commits `07ca27f`, `5bc70f9`); live production checks this session.

Contract digests in `review-request.json` match `dotf spec digest OPS-018-close-out` (features.json, proposal.md, tasks.md). No `[AGENT-DRAFT]`/`[AGENT-SUGGESTION]` tags in the spec folder.

### Spec and task alignment

- All five acceptance criteria map to named tests and all were **re-verified in this session**, not just read from `verification.md`:
  - **AC1**: `tests/test_close_out.py` green (8 passed); the six named giveaways carry `disposition: giveaway`, every item `Sold`, `catalog_opened: 2026-09-25` equals the repository's first commit date (checked with `git log --reverse`).
  - **AC2**: `leaving-denver retro` and `--json` were **run here** and reproduce `verification.md`'s recorded table digit-for-digit (65/60/81 household, 88/100 vehicle, 65/86/99 total; 10 sold, 6 given, 0 unplaced; 45 days; medians 15/45/16); `disagreements: []` — the public dispositions and the private record agree. Sentinel tests (`test_the_command_prints_no_phone_and_no_token`, `test_an_unreadable_private_file_prints_no_total_at_all`) cover the leak and partial-total paths.
  - **AC3**: an end build was made locally: `build/public/` holds **no** phone/303 digit, no `sms:`/`tel:`, no item links, no `$` totals; only `mailto:mlorente@duck.com` (the public alias) and the GitHub profile.
  - **AC4**: case study, README `## Results`, ADR-013 and ADR-008's amendment note all present; the case study publishes percentages/days and no absolute amounts (enforced by `test_the_case_study_publishes_percentages_and_not_money`).
  - **AC5**: `make check` → **1185 passed, 298 skipped** (1183 in verification.md + the two parametrized cases of the post-merge fix), ruff clean, `terraform validate` clean; `scripts/smoke.sh` against production → **`smoke OK (sale over)`**; `/` and `/es/` serve the result page (counts, 45 days, 86 %, `noindex`), `/i/sofa-sleeper/` → HTTP 302, `/seller/` is Access-gated (unchanged; its removal is the decommission runbook's step, out of scope here).
- The **deploy-envelope incident** (`5bc70f9`, lesson-044) is genuinely fixed, not patched over: the expectation now lives in one function (`expected_envelope_holders`) called by a new pre-merge test running **both** build modes with a synthetic envelope, and the deploy-only test reads the mode from `sale_is_over()`. CI on `main` after the merge is green (run 42767637902), so the deploy job's end-mode assertion ran with the real secret and passed.
- Every task in `tasks.md` is ticked **none** — see finding F1.

### Findings

| Severity | Reality | Area | Finding | Evidence | Test (named, or UNTESTED) | Fix location (code / tests / spec / vault) |
|----------|---------|------|---------|----------|---------------------------|---------------------------------------------|
| Minor | REAL | spec hygiene | `tasks.md` is stale: every Implementation and Closing box is unticked although the work shipped and both PRs merged; `verification.md` and the archive checklist carry the real state | tasks.md read at `5bc70f9`; `gh pr list` shows #268/#269 MERGED | UNTESTED (process, not code) | spec artifacts (**contract set** — do not edit now; disposition in `verification.md` or accept: the folder archives as-is with the checklist unticked) |
| Minor | REAL | tooling | The closing checklist's "Type checks pass (`mypy`)" is not runnable: mypy appears nowhere in `pyproject.toml`, `Makefile` or `uv.lock`, and `uv run mypy src` fails ("Failed to spawn: `mypy`") | command output, this session | UNTESTED | code (add mypy config + gate) or spec wording at next spec touch |
| Minor | THEORETICAL | retro arithmetic | An item still `Available` with a private sales record adds its price to `group["realized"]`, and `disagreements()` skips `status != "Sold"`, so the money is counted and the contradiction is never named. Unreachable with the committed data (all 16 items `Sold`, `disagreements: []` in the live run) | code read of `retro.py` (`retro_summary`, `disagreements`); no repro on real data | UNTESTED (`test_an_unplaced_item_is_counted_apart_and_earns_nothing` passes `sales={}`) | code + tests |
| Minor | THEORETICAL | end page | If any item were unplaced, `end_counts` omits `unplaced`, so the page's sentence "{total} items left: {sold} sold, {given} given away" would sum to less than `total` with no third category. Unreachable today (`test_the_split_the_public_page_publishes_is_the_one_the_data_holds` pins 10/6/0) | code read of `site_builder.end_counts` + `sale_over.html`; same as AC3's derived counts | UNTESTED for the unplaced>0 rendering | code + tests |

No Blocker, no Major, no security finding: no secrets in the diff (the private file grew only sops-encrypted sale records), no injection surface (template values come from trusted YAML/locale files), no phone/item/total reaches the public tree (grepped the built output), and the strongest private-data guards (`test_private_isolation.py`, the sealed suites) were **not** among the tests newly skipped for the end of sale.

### Evaluator rubric

| Dimension | Grade (A-D) | Rationale (one line) |
|-----------|-------------|----------------------|
| Correctness        | A | All five ACs verified this session against the built and the live artefact; negative paths (unreadable file, no sales, unknown disposition, leak sentinels) covered by named tests. |
| Verification       | A | `make retro` output reproduced digit-for-digit here; smoke passed against production; `make check` 1185 passed; build tree greps clean — every claim re-ran, not read. |
| Scope              | A | Diff matches the proposal; the three side-changes (CI idempotent `sed`, scratch-car in `sealed_helpers`, envelope-mode test) are each documented in `verification.md`/lessons with reasons. |
| Reliability        | B | Error paths handled (unreadable/no-sales private file exits 1 printing nothing; CI step idempotent); one theoretical error path unhandled and unnamed (F3). |
| Maintainability    | A | Small pure functions (`retro_summary` takes data as arguments), CC well under 10, comments explain WHY; 300+ lines of new tests for new logic. |
| Handoff-readiness  | B | Lesson-043, lesson-044, ADR-013, case study and verification.md are complete and honest; `tasks.md` state is not maintained (F1). |

### Verdict

**PASS WITH GAPS** — no Blocker, no REAL Major, rubric all B or above; the four findings are Minors (two REAL process/tooling, two THEORETICAL, both unreachable with the committed data), each tracked above with its disposition target.

### Recommended next steps

Per the review's set rules, `proposal.md`, `tasks.md` and `features.json` are **closed** by this verdict — the contract set must not change, or the review is invalidated. These go to the implementer to disposition in `verification.md` (applied / ticketed / declined with a reason), or into follow-up tickets:

- **F1 (tasks.md ticks)** — accept as-is: the archive checklist in `verification.md` is the live state and the work is merged; record that decision, or tick the boxes only if the archive gate permits without digest churn.
- **F2 (mypy)** — either add mypy to the dev deps and `make check`, or drop the word "mypy" from the closing checklist at the next spec touch; as committed, the claim has no runner.
- **F3 (unplaced item with a sales record)** — worth a small follow-up: have `disagreements()` flag `status != "Sold"` items that carry a private sales record, and skip their price in `realized` (or name it); add a test with a sales record on an `Available` item.
- **F4 (unplaced rendering)** — fold into the same follow-up: pass `unplaced` into the template or make the sentence name the remainder; a test rendering `unplaced > 0` would close it.

`dotf spec archive OPS-018-close-out` is **advisable** in the current state: the verdict is passing, the digests match, and the gaps above are tracked rather than blocking. Before archiving, the decommission runbook's ordering still applies (page ✓ done here → credentials → archive).
