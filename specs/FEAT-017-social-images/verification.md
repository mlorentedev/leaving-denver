---
tags: [spec, verification]
created: "2026-10-06"
---

# Verification - FEAT-017-social-images

## Evidence

- [x] AC1 -> `test_the_build_writes_the_page_and_both_images_at_their_sizes`, `test_the_page_shows_both_images_the_caption_and_one_link_per_network`, `test_the_page_is_hidden_scriptless_and_self_contained`, `test_the_font_is_the_sites_own_and_loads`
- [x] AC2 -> `test_the_story_qr_is_exactly_the_instagram_url` (module centres sampled against `segno`'s matrix), `test_the_built_story_carries_the_instagram_url` (mutation-checked: building the story with the facebook URL fails it), `test_the_story_leaves_instagrams_bands_empty`
- [x] AC3 -> `test_the_collage_takes_the_car_then_one_per_category_then_by_price`, `test_a_sold_item_is_never_in_the_collage_and_the_car_leaves_once_sold`, `test_an_item_without_a_photo_is_skipped`, `test_the_post_draws_as_many_cells_as_it_has_photos[1|2|3|5]`
- [x] AC4 -> `test_neither_the_page_nor_the_copy_holds_a_contact_a_price_or_a_date`, `test_the_copy_names_what_is_still_for_sale`, `test_the_caption_names_the_car_while_it_is_unsold`
- [x] AC5 -> `test_the_end_build_makes_no_social_directory_and_sweeps_a_stale_one`
- [x] AC6 -> `test_every_channel_the_site_can_link_from_is_a_known_source` now includes `social.SOURCES`
- [x] AC7 -> `test_nothing_else_links_to_the_social_page`, `tests/test_class_coverage.py` with `social.html`

## Test status

- `uv run pytest` -> 1342 passed, 8 skipped (unit and browser); `ruff` clean
- Rendered with the real covers into the scratchpad and inspected: the post shows the car on top with sofa, monitor, topper and TV under it, then the copy and the address; the story shows the heading, the QR, "Scan, or tap the link", the address and the Spanish line, with both of Instagram's bands empty.
- Pending, owner: scan the story's QR from a second phone after deploy.

## Decisions made during implementation

- `post.jpg`, not PNG: a photo collage in PNG is several MB for nothing (about 300 KB as JPEG). The story stays PNG: flat colours, about 50 KB, crisp modules.
- Cells crop their photo to fill (`ImageOps.fit`); the catalog keeps whole photos.
- The page has no copy buttons, so it needs no script and no CSP hash: the caption sits in a `<pre>` to long-press and copy.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? no: nothing surprising came up; the format choices are recorded above
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: an unlinked, scriptless page under the existing CSP adds no origin and no contract
- [x] New pattern candidate for `00_meta/patterns/`? no: social image sizes are specific to this sale

## Independent review (2026-10-08)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer. It worked read-only on main at 077360f, checking each criterion against the code and the tests. The `features.json` commands were run again on 9659d65 before archiving, and all of them pass.

- Verdict: ready.
- AC1–AC7 hold.
- `features.json` was the unfilled scaffold (`echo 'not implemented'`). This archive replaces it with one command per criterion, and all seven pass. AC7 builds first, because the class-coverage test reads `build/`.
- The QR is checked module by module against `segno`, not decoded by a camera. The owner's phone scan is #210.
