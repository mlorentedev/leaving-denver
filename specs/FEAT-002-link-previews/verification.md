---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - FEAT-002-link-previews

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [x] AC1 -> `test_robots_lets_preview_crawlers_in_and_keeps_everyone_else_out`; `test_robots_txt_disallow_all` still green
- [x] AC2 -> `test_each_published_item_has_a_share_page[en/es]`
- [x] AC3 -> `test_share_pages_leak_nothing_unpublished_and_no_contact`, `test_an_item_without_a_photo_has_no_preview_image`, `test_template_sees_only_sanitized_data`, `test_unpublished_item_and_its_bundles_are_absent_from_public`
- [x] AC4 -> `test_preview_image_is_letterboxed_not_cropped`, `test_preview_image_is_rewritten_only_when_it_changes`, `test_a_new_cover_prunes_the_old_preview`
- [x] AC5 -> `test_catalog_pages_carry_their_own_preview[en/es]`
- [x] AC6 -> `test_deep_link_opens_the_item_after_load` (static) and headless Chrome (below)
- [x] AC7 -> `test_a_site_url_that_is_not_a_bare_https_origin_fails` (4 cases), `test_site_url_comes_from_the_environment`
- [ ] AC8 -> PR 2

## Test status

- Test suite: `make check` -> ruff clean, 254 passed
- Headless Chrome (`--dump-dom`) over the real build:
  - `es/index.html#sofa-sleeper` -> `<dialog id="itemSheet" ... open>`, with the sofa's Spanish title;
  - `#nope` -> sheet closed;
  - over HTTP, `/es/i/sofa-sleeper/` -> `<html lang="es">` with the sofa sheet open. The redirect works end to end.
- `scripts/smoke.sh` against the build served by `python -m http.server`: the new robots, `og:image` and share-page checks pass. It stops later at `_headers`, which only Pages applies.
- The real build has 13 share pages per locale and 13 preview images (124-172 KB). The sofa's is letterboxed, with the whole sofa in frame.
- No regressions in the existing suite: yes

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- The body carries a plain link rather than `<noscript>`. It is also the way on if the redirect is slow, and it costs nothing.
- Share pages are removed and rebuilt on every build, like `index.html`. A page left by an item unpublished since keeps its title public otherwise.
- The preview image is built from the processed cover JPEG, not the source. It inherits the EXIF scrub and the size cap, and its freshness is decided by comparing the encoded bytes. No manifest entry is needed.
- `test_template_sees_only_sanitized_data` merged every render's context into one set. It now keeps one set per template, so the share pages' smaller context is asserted too.

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
