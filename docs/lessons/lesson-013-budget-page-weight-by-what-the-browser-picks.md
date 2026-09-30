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

`test_phone_downloads_a_third_of_the_full_covers` replays the browser's choice (smallest
candidate ≥ 360 device px, a 2-column phone at DPR 2) over the built page and asserts the
picks weigh under a third of the full JPEGs. Measured at introduction: 5.11 MB → 0.54 MB.
Dropping `srcset` from a card, or a variant step that stops shrinking, fails it.
