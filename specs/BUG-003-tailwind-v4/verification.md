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

## Promotion candidates

- [ ] Lesson? Decide at archive time.
- [ ] ADR? Decide at archive time.
- [ ] Pattern? Decide at archive time.

## Archive checklist

- [ ] Independent review and archive after PR acceptance; do not close issue merely for opening a PR.
