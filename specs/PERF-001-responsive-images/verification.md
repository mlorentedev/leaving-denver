---
tags: [spec, verification, templates]
created: "2026-09-29"
---

# Verification - PERF-001-responsive-images

## Evidence

- [x] AC1 -> `test_wide_photo_gets_every_variant_upright_and_without_exif`, `test_narrow_photo_is_never_upscaled`
- [x] AC2 -> `test_every_catalog_img_is_responsive[en|es]`, `test_photo_set_lists_variants_then_the_jpeg`
- [x] AC3 -> `test_vehicle_hero_loads_first[en|es]`, `test_item_dialog_uses_srcset`
- [x] AC4 -> `test_up_to_date_outputs_are_not_rewritten`, `test_a_missing_variant_is_rebuilt`
- [x] AC5 -> `test_phone_downloads_a_third_of_the_full_covers`

## Test status

- `make check` -> 126 passed (ruff clean)
- Baseline (live, 2026-09-29): 13 unique cover/hero JPEGs = 5.11 MB
- After (built page, candidates a DPR-3/2 phone picks for each slot): 13 files = 0.54 MB (-89%)
- Preview smoke (feat-responsive-images.leaving-denver.pages.dev, Chrome): EN/ES 200; 45 srcset candidates all 200 with image/webp or image/jpeg; cards pick 480w, hero 800w, dialog main photo 800w and thumbnails 480w; thumbnail click swaps the photo; no console errors

## Decisions made during implementation

- Variants are a parallel `photos` field; `images` (YAML, poster assistant, JSON consumers) is untouched (lesson-012).
- The canonical JPEG stays the largest `srcset` candidate, so desktop/retina still gets full quality and no variant is ever upscaled.
- Freshness = JPEG and every variant its width calls for exist with mtime >= source; a deleted or older variant is rebuilt (CodeRabbit), and variants outside the current widths are pruned (PR-Agent).
- Fonts shipped separately in #90: one 27 KB variable woff2 replaces five Google Fonts weights; verified on its preview and on production.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-013-budget-page-weight-by-what-the-browser-picks.md
- [x] ADR-worthy decision? no: responsive variants are an implementation detail inside ADR-003's build, no new component or dependency (Pillow already writes WebP)
- [x] New pattern candidate for `00_meta/patterns/`? no: single project so far

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/PERF-001-responsive-images/` -> `specs/archive/PERF-001-responsive-images/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
