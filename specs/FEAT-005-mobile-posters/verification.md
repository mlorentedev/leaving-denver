---
tags: [spec, verification, templates]
created: "2026-09-29"
---

# Verification - FEAT-005-mobile-posters

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [x] AC1 -> `test_mobile_poster_uses_only_published_sanitized_inventory`,
  `test_mobile_poster_does_not_offer_sold_pending_or_free_items`,
  `test_mobile_copy_uses_public_price_and_singular_voice`,
  `test_mobile_copy_links_to_each_public_item_with_platform_attribution`
- [x] AC2 -> `test_access_middleware_fails_closed_without_configuration`,
  `test_access_middleware_rejects_missing_jwt_when_configured`; local Wrangler
  served `/seller`, `/seller/`, `/seller/index.html`, `/seller/seller.mjs` and
  encoded/normalized paths as `503`, while `/` returned `200`.
- [x] AC3 -> `make check` plus `tests/test_security_isolation.py`
- [x] AC4 -> `test_mobile_access_setup_is_documented`; owner login smoke is
  pending Zero Trust configuration.

## Test status

- Test suite after merging `origin/main`: `make check` -> 279 passed, 6 skipped;
  Wrangler Pages dev compiled the root Functions route.
- Manual smoke test: local anonymous Pages catalog `/` and `/es/` returned
  `200`; `/seller/`, its HTML and JS, and an encoded seller path returned
  `503`. Production
  owner/anonymous Access check remains pending external account configuration.
- No regressions in existing test suite: yes.

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- A separately generated public-only poster can safely exist behind Access
  without depending on Access for its data-isolation guarantee. The local
  reserve-price assistant stays local.
- Access application policy and runtime bindings are deliberately external;
  no success-shaped fallback serves `/seller/` before they exist.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [ ] Lesson for the repo's `docs/lessons/`? <yes: path / no: reason>
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? <yes: path / no: reason>
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. <yes: path / no: reason>

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-005-mobile-posters/` -> `specs/archive/FEAT-005-mobile-posters/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
