---
tags: [spec, verification]
created: "2026-09-29"
---

# Verification - BUG-003-tailwind-v4

## Evidence

- [x] AC1: `test_public_pages_ship_local_css` checks EN/ES links, local files, no runtime CDN.
- [x] AC2: `test_private_assistant_uses_local_css` checks local private asset and public isolation.
- [x] AC3: `test_compiled_css_contains_v4_utilities` checks actual compiled declarations and font.
- [x] AC4: `test_missing_cli_fails_direct_build` checks fail-closed even when old CSS exists; direct `uv run leaving-denver build` and `make check` build via pinned CLI.

## Test status

- RED: `uv run pytest -q tests/test_tailwind_build.py` → 5 failures (missing stylesheet/CDN still present/missing CLI did not fail).
- GREEN: `uv run leaving-denver build` then `uv run pytest -q tests/test_tailwind_build.py` → 5 passed.
- Full suite: `make check` → Ruff clean and 92 passed (baseline 87).
- GitHub Actions `test` check passed on PR #83 (deploy skipped, as expected for a pull request).
- npm lock: `npm ci --dry-run --ignore-scripts` succeeded; package-lock includes Linux and Windows optional binaries.
- Deploy smoke: `scripts/smoke.sh` now checks `/styles.css`, both language links and absence of play CDN; production Pages deployment is intentionally not performed in this PR.
- Public compiled CSS is 23,918 bytes and private CSS 18,494 bytes locally; no reserve-price markers in either.
- PR: https://github.com/mlorentedev/leaving-denver/pull/83 (`Closes #8`; not merged).

## Decisions made during implementation

- Explicit `@source` per template prevents the public stylesheet from scanning private markup; private CSS stays under `build/private/`.
- The CLI runs within direct Python builds as well as Make, and must be installed via `npm ci`; compilation stages each output before replacing it.

## Independent adversarial review (2026-09-30)

Reviewer: the `reviewer` subagent, not the implementer, at main `908b1e3`. It ran a fresh `npm ci` from the lockfile and checked every template class token, including JS `className` strings, against the compiled CSS. Nothing was missing. `@source` scopes are correct, with no private markup in the public CSS. Verdict: **PASS-WITH-GAPS.**

| # | Finding | Disposition |
|---|---|---|
| 1 | Coverage is proven for four utilities only; Tailwind drops unknown classes silently | **Ticketed** #103 |
| 2 | Assertions match minified output byte for byte, so they are brittle to Dependabot bumps | **Ticketed** #103 |
| 3 | The "fail-closed even when old CSS exists" claim is not exercised by the test | **Ticketed** #103. The claim stands on code reading only. |
| 4 | Tests can read a stale `build/`; no `engines` field | **Ticketed** #103 (`engines`). The stale-build risk is covered by the `make build` prefix in `features.json`. |

## Promotion candidates

- [x] Lesson? yes: docs/lessons/lesson-015-check-classes-against-the-compiled-css.md (from this spec's review, shipped under BUG-009)
- [x] ADR? no: compiling Tailwind with its pinned CLI is a build detail inside ADR-003, no new component
- [x] Pattern? no: single project

## Archive checklist

- [x] Independent review and archive after PR acceptance; do not close issue merely for opening a PR. Launcher review waived by the owner on 2026-09-30, see `review_waived_reason` in proposal.md.
