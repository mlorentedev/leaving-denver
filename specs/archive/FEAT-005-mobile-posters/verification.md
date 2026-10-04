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
  `test_access_middleware_rejects_missing_jwt_when_configured`,
  `test_access_middleware_requires_signed_jwt_audience_and_expiration`;
  a signed token is admitted only with matching audience, issuer and expiration.
  Local Wrangler and the real Pages preview alias and deployment hostname
  served `/seller`, `/seller/`, `/seller/index.html`, `/seller/seller.mjs` and
  encoded paths as `503`, while `/` and `/es/` returned `200`.
- [x] AC3 -> `make check` plus `tests/test_security_isolation.py`
- [x] AC4 -> `test_mobile_access_setup_is_documented`; owner login smoke is
  pending Zero Trust configuration.

## Test status

- Test suite after merging `origin/main` including #122, #123, #125 and #126:
  `make check` -> 297 passed, 24 browser tests skipped on Windows.
  The preceding `make deploy BRANCH=seller-access-smoke` passed 287 tests
  before #123 merged, then deployed a Pages preview Functions bundle.
- Manual smoke test: both `seller-access-smoke.leaving-denver.pages.dev` and
  the immutable `7ab46028.leaving-denver.pages.dev` returned `200` for
  `/` and `/es/`; every seller path above returned `503`. Production
  owner/anonymous Access check remains pending external account configuration.
- No regressions in existing test suite: yes.

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- A separately generated public-only poster can safely exist behind Access
  without depending on Access for its data-isolation guarantee. The local
  reserve-price assistant stays local.
- Access application policy and runtime bindings are deliberately external;
  no success-shaped fallback serves `/seller/` before they exist.

## Independent review (2026-10-03)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer, worked read-only on main at 2cdc798, and ran the `features.json` commands plus the full suite on a clean copy (1042 passed, 2 skipped).

- Verdict: archive with a note. AC1, AC2 and AC4 hold; anonymous `/seller/` answers 302 to Cloudflare Access on production.
- AC3 is half superseded: the local poster assistant was retired in #146.
- Owner-run Access checks: anonymous denial and owner OTP login were recorded on 2026-09-30 and 2026-10-02 (#17). The unlisted-identity denial was not recorded; it is not an AC, and the middleware verifies the JWT on its own.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-018-defer-shell-token-substitution-in-make.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: docs/adr/adr-007-private-seller-data-travels-as-ciphertext.md
- [x] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. no: single project

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-005-mobile-posters/` -> `specs/archive/FEAT-005-mobile-posters/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
