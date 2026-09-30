---
tags: [spec, tasks]
created: "2026-09-29"
---

# Tasks - BUG-003-tailwind-v4

## Setup

- [x] Confirm isolated `fix/tailwind-v4-build` worktree at 97b6ed8 and open issue #8.
- [x] Fill proposal and cross-check every criterion against implementation tasks.

## Implementation

- [x] [AC1] [AC2] Add `tests/test_tailwind_build.py` assertions for EN/ES/private HTML local links and no runtime CDN; run `uv run pytest -q tests/test_tailwind_build.py` (RED: CDN link absent and CSS absent).
- [x] [AC3] Add compiled-CSS content assertions for v4-only selectors and theme font to `tests/test_tailwind_build.py`; run same command (RED: stylesheet missing).
- [x] [AC4] Add direct build failure regression test using monkeypatched CSS toolchain in `tests/test_tailwind_build.py`; run targeted pytest (RED: build succeeds without CSS).
- [x] [AC1] [AC2] [AC3] [AC4] Add pinned `package.json`/`package-lock.json`, `src/leaving_denver/{public,private,theme}.css`, CSS build step in `src/leaving_denver/site_builder.py`, and replace CDN/config scripts in both HTML templates; run targeted pytest (GREEN: 5 passed).
- [x] [AC4] Update `Makefile`, `.github/workflows/ci.yml`, `README.md` and `docs/runbooks/ops.md` to install locked npm deps in CI and describe Node prerequisite; run `make check` (GREEN: 92 passed).

## Closing

- [x] Run `make check` (92 passed), inspect CSS and public/private isolation, record results in `verification.md`.
- [x] Commit on isolated branch with trailer and open PR #83 with `Closes #8` (do not merge).

## Machine-readable features

`features.json` maps AC1–AC4 to executable regression selectors. Only the harness may set `state: passing`.
