---
id: "lesson-budget-page-weight-by-what-the-browser-picks"
type: lesson
scope: local
tags: [performance, images, testing]
created: "2026-09-30"
source: "PERF-001 (#20): the live catalog shipped 5.1 MB of photos"
---

# Lesson: Budget Page Weight by What the Browser Picks

## Context

Every card, the vehicle hero and the 48 px bundle thumbnails loaded the same 1500–1600 px
JPEG. The "<300 KB per image" rule in the image processor held, yet a phone still pulled
5.1 MB for 13 covers because nothing asked which file a given slot needed.

## Finding

A per-file size limit does not bound what a page costs. Once `srcset` exists, the files on
disk also stop being what gets downloaded: the browser takes the smallest candidate at least
`sizes × DPR` wide. A budget measured on disk either passes trivially or never fails.

## Guard

`test_phone_downloads_a_third_of_the_full_covers` replays the browser's choice over the built
page: for each cover it resolves the image's own `sizes` at the viewport, multiplies by the
DPR, and takes the smallest candidate at least that wide. The picks must weigh under a third
of the full JPEGs at 390 px DPR 2, 390 px DPR 3 and 430 px DPR 3. Hard-coding a slot width
instead of reading `sizes` hides the regression that matters: a card whose `sizes` grows to
`100vw`, which `test_the_budget_catches_a_card_sized_to_the_viewport` pins.

Always state the DPR next to a weight figure. Measured on the built page:

| Case | Covers vs full JPEGs |
|---|---|
| Introduction (PERF-001), 390 px DPR 2 | 5.11 MB → 0.54 MB (11%) |
| PERF-002, 390 px DPR 2 | 9% |
| PERF-002, 390 px DPR 3 | 26% |
| PERF-002, 430 px DPR 3 | 27% |

A DPR 3 phone at 430 px needs about 1290 px for the full-width hero. That is more than the
1200w variant, so before PERF-002 the browser fell back to the 346 KB JPEG. A 1600w WebP, as
wide as the JPEG cap, replaces the JPEG in `srcset` (207 KB), and
`test_a_dpr3_phone_never_falls_back_to_the_hero_jpeg` holds it there.
