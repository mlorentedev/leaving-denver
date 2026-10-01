---
tags: [spec, tasks, templates]
created: "2026-09-30"
---

# Tasks - FEAT-009-one-seller-tool

> TDD order. PR 1 (the public-safe copy) first, then PR 2 (`pr2-encrypted-private-data.md`,
> ADR-007), tracked in its own section below.

## Setup

- [x] Branch `feat/one-seller-tool-copy` created from main
- [x] `proposal.md` states testable acceptance criteria
- [x] `dotf spec init` could not run (GitHub auth was invalid, so the issue gate failed);
  the folder was scaffolded by hand from FEAT-008's four files

## Implementation

- [x] [AC1-AC8] Write `tests/test_seller_copy.py`; run
  `uv run pytest -q tests/test_seller_copy.py` (expected FAIL: no `CONFIG`, no replies).
- [x] [AC9] [AC11] Extend `tests/test_mobile_poster.py` (private markers, the local assistant
  stays out of the public build), `tests/test_security_isolation.py` (template context),
  `tests/test_inventory_ssot.py` (the new files join the car-copy and unbacked-claim guards),
  `tests/test_poster_voice.py` (the seller tool, English and Spanish).
- [x] [AC10] Let the browser harness inline a page's module script (file:// blocks it) and
  write `tests/test_seller_browser.py`.
- [x] [AC8] Add `data/seller-replies.yaml` (six replies, English and Spanish).
- [x] [AC1-AC3] Build the payload in `site_builder.py` (`seller_items`, `seller_payment`,
  `seller_replies`, `write_seller_poster`): Spanish overlay, payment terms from data and
  locales, month and origin.
- [x] [AC1-AC7] Rewrite `assets/seller.mjs`: channel table, Spanish, vehicle copy, flaws
  last, limits, links, creator links, tags, price, full listing.
- [x] [AC8] [AC10] Rework `templates/seller.html`: six channels, counters, creator link,
  tags, photos, the replies section.
- [x] Guard the defect class the change exposed: a class written only in a script is never
  compiled. `public.css` scans `seller.mjs`, and `tests/test_class_coverage.py` now covers
  `seller.html` and `seller.mjs` (it failed without the `@source` line).
- [x] Update `docs/runbooks/seller-playbook.md` and `docs/runbooks/ops.md`.
- [x] Run `make check`.

## PR 2: sealed private data (branch `feat/seller-sealed-private-data`)

- [x] [AC6] [AC7] `data/eff_large_wordlist.txt` (EFF source and licence in the header) and
  `assets/seal.mjs` + the page's `sealEnvelope`/`openEnvelope`; `tests/test_sealed_envelope.py`.
- [x] [AC1] [AC2] [AC8] `site_builder.sealed_envelope`, the sealed block and the unlock section in
  `seller.html`; `tests/test_sealed_build.py`.
- [x] [AC3] [AC7] `seller.mjs` unlock, views, Lock, pagehide; `tests/test_sealed_browser.py`
  (headless Chrome). Mutation-checked: no pagehide, Lock that keeps the views, and a wrong
  passphrase that renders a view each fail a test.
- [x] [AC4] [AC5] [AC10] `seal.py` and `leaving-denver seal`; `make ci-secrets` ends with it;
  `tests/test_seal_command.py` stubs the TTY, `gh` and the Node child.
- [x] [AC2] The deploy job requires `SELLER_SEALED`; `tests/test_cd_workflow.py`.
- [x] [AC9] The CSP in `functions/_middleware.js`, inline code out of `seller.html`;
  `tests/test_seller_csp.py`; `test_no_csp_stops_the_cloudflare_beacon` narrowed.
- [x] [AC4] [AC14] [AC15] [AC16] Owner's passphrase decisions: Enter generates (ci-secrets only) and
  saves to Bitwarden through dotf, else a TTY print and a typed-back confirmation; no generation on
  re-seal; `SELLER_PASSPHRASE` from the environment; the hidden username field.
- [x] [AC14] `cli.offer_seller_update` after post, reprice and sold; `tests/test_update_offer.py`.
- [x] [AC12] Remove the panel, the poster assistant, its PIN, `build/private/` and `make panel`;
  the row logic moves to `seller.mjs` (`tests/test_seller_private_logic.py`);
  `tests/test_private_isolation.py`.
- [x] [AC13] Runbook, playbook, architecture notes, ADR amendments; `tests/test_ops_runbook.py`.
- [x] Guards for the defects found: every wordlist word survives being typed back; `gh` never
  inherits the terminal; the autouse guards in `tests/conftest.py` (no real `gh`, no TTY).
- [x] Review round 2 (F1-F9): see `verification.md`.
- [ ] [AC9] [AC11] Owner: the served header after an Access login, and the unlock time on the
  phone (`verification.md`).

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff (no scope creep)
- [x] `verification.md` filled in
- [x] PR 1 merged
- [ ] PR 2 opened as a draft; not merged until the owner has run `make ci-secrets`
