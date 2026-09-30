---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-002-link-previews

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [x] AC1 -> `test_robots_lets_preview_crawlers_in_and_keeps_everyone_else_out` (read with `urllib.robotparser`: 5 preview bots allowed, Googlebot, bingbot, GPTBot, CCBot and Slackbot refused); `test_robots_txt_disallow_all` still green
- [x] AC2 -> `test_each_published_item_has_a_share_page[en/es]`, `test_markup_in_a_title_stays_text`
- [x] AC3 -> `test_share_pages_leak_nothing_unpublished_and_no_contact`, `test_an_item_without_a_photo_has_no_preview_image`, `test_template_sees_only_sanitized_data`, `test_unpublished_item_and_its_bundles_are_absent_from_public`
- [x] AC4 -> `test_preview_image_is_letterboxed_not_cropped`, `test_preview_image_is_rewritten_only_when_it_changes`, `test_a_new_cover_prunes_the_old_preview`
- [x] AC5 -> `test_catalog_pages_carry_their_own_preview[en/es]`
- [x] AC6 -> `test_deep_link_opens_the_item_after_load` (static) and headless Chrome (below)
- [x] AC7 -> `test_a_site_url_that_is_not_a_bare_https_origin_fails` (4 cases), `test_site_url_comes_from_the_environment`, `test_an_item_id_that_is_not_a_slug_fails` (5 cases)
- [x] AC8 -> `test_item_sheet_has_a_share_button[en/es]`, `test_the_shared_url_is_the_items_share_page[en/es]` (the URL the button builds is the share page's own `og:url`), `test_share_falls_back_to_copying_the_link`, `test_share_strings_exist[en/es]`. A 390 px headless screenshot of `/es/#sofa-sleeper` shows Share between "Escribir sobre este artículo" and Close, on one row.

## Test status

- Test suite: `make check` -> ruff clean, 260 passed (PR 1), 267 passed (PR 2)
- Headless Chrome (`--dump-dom`) over the real build:
  - `es/index.html#sofa-sleeper` -> `<dialog id="itemSheet" ... open>`, with the sofa's Spanish title;
  - `#nope` -> sheet closed;
  - over HTTP, `/es/i/sofa-sleeper/` -> `<html lang="es">` with the sofa sheet open. The redirect works end to end.
- `scripts/smoke.sh` against the build served by `python -m http.server`: the new robots, catalog `og:image` and EN/ES share-page checks pass. It stops later at `_headers`, which only Pages applies.
- The real build has 13 share pages per locale and 13 preview images (124-172 KB). The sofa's is letterboxed, with the whole sofa in frame.
- No regressions in the existing suite: yes

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- The body carries a plain link rather than `<noscript>`. It is also the way on if the redirect is slow, and it costs nothing.
- Share pages are removed and rebuilt on every build, like `index.html`. A page left by an item unpublished since keeps its title public otherwise.
- The preview image is built from the processed cover JPEG, not the source. It inherits the EXIF scrub and the size cap, and its freshness is decided by comparing the encoded bytes. No manifest entry is needed.
- `test_template_sees_only_sanitized_data` merged every render's context into one set. It now keeps one set per template, so the share pages' smaller context is asserted too.

- PR 2 builds the shared URL from the catalog's own `og:url` meta tag plus `i/<id>/`, rather than from a new template variable. The tag already holds the locale's absolute root, and a test pins the result to the share page's `og:url`, so the two cannot drift.

## Independent review (reviewer subagent, 9a0405f): PASS-WITH-GAPS

No blocker. Dispositions, applied in the next commit unless noted:

| # | Finding | Disposition |
|---|---|---|
| 1 | `build_public_site` rose from CC 24 to 35 | **Applied.** `catalog_og` (B 8) and `write_share_pages` (A 3) extracted; `build_public_site` is back to D 24, its level before this PR. |
| 2 | Item ids are not validated, and `../x` would write outside `i/` | **Applied.** The sanitizer requires lower-case slugs; `test_an_item_id_that_is_not_a_slug_fails`. |
| 3 | The hash stays after the sheet closes, so a reload reopens it | **Applied.** The hash is dropped with `replaceState` before the sheet opens. |
| 4 | `../../#id` depends on the trailing slash | **Declined.** Pages redirects `/i/x` to `/i/x/`, it is the only host, and the share URLs are generated with the slash. |
| 5 | The spec named `<cover>-og.jpg`, but the code writes `og/<cover>.jpg` | **Applied** to the proposal. |
| 6 | Smoke did not check the share page's own `og:image`, nor the ES page | **Applied.** Both locales' pages and their images are checked. |
| 7 | The deep-link test is static, and the browser proof is prose | **Declined.** The repo has no browser test harness (lesson-014), and adding one is larger than this feature. The headless runs above are the record. |
| 8 | No test for markup in a title, and robots is read by string split | **Applied.** `test_markup_in_a_title_stays_text`; robots is read with `urllib.robotparser`. |
| 9 | Pruning `og/` would fail on a subdirectory | **Applied.** Only files are pruned. |
| 10 | A cover under 630 px tall sits small on the canvas | **Declined.** Covers are phone photos capped at 1600 px, and upscaling would only blur them. |
| 11 | `es_ES` vs `es_US`; Slackbot, Discordbot and LinkedInBot not allowed | **Declined.** `og:locale` only labels the language of the tags, and the card renders the same either way. The sale is not shared on Slack, Discord or LinkedIn. |

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [x] Lesson for the repo's `docs/lessons/`? no: the one non-obvious rule (redirect people with JavaScript, never crawlers) is recorded in ADR-004 and in the share template
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? yes: docs/adr/adr-004-allow-link-preview-crawlers.md
- [x] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. no: one static site

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-002-link-previews/` -> `specs/archive/FEAT-002-link-previews/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
