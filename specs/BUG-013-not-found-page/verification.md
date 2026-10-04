---
tags: [spec, verification]
created: "2026-10-01"
---

# Verification - BUG-013-not-found-page

## Evidence

- [x] AC1 (both modes) -> `tests/test_not_found.py::test_the_build_writes_a_top_level_404[catalog|end]`; `tests/test_end_of_sale.py::test_nothing_but_the_end_page_and_its_plumbing_is_published` (published set is the old one plus `404.html`).
- [x] AC2 (bilingual, linked, noindex) -> `::test_the_page_says_so_in_both_languages`, `::test_each_language_links_to_its_own_home_page`, `::test_the_page_stays_out_of_search`.
- [x] AC3 (no contact, no item data) -> `::test_the_page_carries_no_phone_in_any_form` (sentinel `+13035550100`, six formats, `sms:`, `tel:`, `const _C`, `<script`), `::test_the_page_names_no_item_and_no_price`. The existing security tests walk `build/public` with `rglob`, so they read the live `404.html` too.
- [x] AC4 (any depth) -> `::test_every_reference_resolves_to_the_same_place_from_any_depth[/|/es/|/i/sofa-sleeper/|/a/b/c/d/e]`, `::test_every_reference_is_a_file_of_the_site`, `::test_the_page_uses_the_compiled_stylesheet`. Why root-absolute: Pages serves the file at the requested URL, so a relative path would resolve against the missing path's directory.
- [x] AC5 (end sweep and redirects) -> `::test_the_end_build_keeps_the_page_when_it_sweeps_a_catalog_away`, `::test_the_end_redirects_do_not_swallow_the_page`.
- [x] AC6 (smoke) -> `tests/test_smoke_script.py::test_an_unknown_path_that_answers_200_fails`, `::test_a_404_that_is_not_the_not_found_page_fails`; `tests/test_smoke_end_of_sale.py::test_smoke_fails_when_an_unknown_path_answers_200`, `::test_smoke_fails_when_the_end_build_has_no_not_found_page`. The stubs (`tests/pages_stub.py`) answer a missing path as Pages does with and without a `404.html`.
- [x] AC7 (CSS) -> `tests/test_class_coverage.py` with `not_found.html` registered.

## Test status

- `SELLER_PHONE=+13035550100 make check` -> `739 passed, 1 skipped in 85.36s`, ruff clean (main before the change: 653 passed at OPS-011; this adds the 404 tests and the smoke cases).
- The same gate with `seller.sale_over: true` in a scratch edit (reverted, `git status` clean), run as `env -u SELLER_PHONE -u SELLER_SEALED make check` -> `576 passed, 164 skipped in 51.12s`. The new `test_not_found.py` builds scratch sites in both modes, so it runs in both.
- The four new smoke tests, run against the previous `scripts/smoke.sh`: `4 failed`; against the new one: `4 passed`.
- Not run: a real Pages deploy. The smoke on the first deploy after merge confirms the 404 status and body. It does not read the 404 response's headers, so `X-Robots-Tag: noindex` from `_headers` on that response stays unverified. The page also carries a robots meta tag with `noindex`, which covers it either way; check once with `curl -sI <deployment>/x-not-found/`.

## What relied on the SPA fallback

- **Deep links** are `/#<id>` fragments: the server only sees `/`. Unaffected.
- **Share pages** `/i/<id>/` and `/es/i/<id>/` are real files (`index.html` in a directory). Unaffected; a share path of an unpublished item is now a 404, as it should be, and in the end build `_redirects` still sends them to the end page (a redirect rule is matched before the 404).
- **`/seller` without a slash** and `/seller/*`: `functions/_middleware.js` runs before static assets and gates `/seller` and `/seller/*` on the Access token before any asset or 404 decision, then calls `context.next()` for everything else. A path outside `/seller` reaches Pages' asset lookup and gets the 404 page; one inside is gated first. For the owner behind Access, a missing `/seller/x` is now the 404 page instead of the catalog. In a catalog build `/seller` still redirects to `/seller/` (a directory with an `index.html`). In the end build there is no `seller/`, and an anonymous `/seller/` stays a redirect to the Access login (rehearsed in OPS-011), not a 200.
- **`/es` without a slash** and `/flyer` without one: directory index redirects by Pages, as before. In the end build `/flyer` is a `_redirects` rule.
- **The uptime monitor** fetches `/` (a real file) for its keyword. Unaffected.
- **`scripts/smoke.sh`** assumed unknown paths answer 200 in two comments and in `share_page`'s content check; the comments are updated, and `share_page` now fails on a 404 through `get`'s `-f`, with retries, which is stricter and correct.

## Decisions made during implementation

- One bilingual page, root-absolute assets, no Open Graph tags (nothing to preview).
- The end build emits it too: otherwise Pages would run the end site as an SPA and serve the end page for every path, which hides stale links the same way.
- Copy in `locales/not_found.yaml`, as the flyer's is in `locales/flyer.yaml`, so the catalog's inline `ui_json` does not grow.
- `404.html` is built from a template with no inventory input: there is nothing to sanitize because nothing is passed in.

## Independent review (2026-10-03)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer, worked read-only on main at 2cdc798, and ran the `features.json` commands plus the full suite on a clean copy (1042 passed, 2 skipped).

- Verdict: archive. AC1-AC7 hold; the live 404 answers with `x-robots-tag: noindex` and the bilingual page, which closes the open item above.
- The smoke flake the reviewer found (a fresh deployment answering 404 with another body) was ticketed as #173 and fixed in #175.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-026-one-404-page-is-served-at-every-missing-url.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: a page and its smoke check, no new constraint on later work.
- [x] New pattern candidate for `00_meta/patterns/`? no: nothing recurs across projects yet.

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/BUG-013-not-found-page/` -> `specs/archive/BUG-013-not-found-page/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
