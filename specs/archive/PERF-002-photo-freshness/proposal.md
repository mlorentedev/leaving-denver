---
id: "PERF-002-photo-freshness"
type: spec
status: archived # draft | implementing | verifying | archived
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#101"
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-09-30: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. Reviews on record: independent reviewer subagent on #110 (6033b61) and #111 (60af84f); CodeRabbit on #110 (0ca3616) and #111 (8d9102b)."
tags: [spec, proposal]
template_version: "1.0"
---

# PERF-002-photo-freshness

## Why

<!-- from issue #101: gaps found by the independent PERF-001 review -->

The PERF-001 review reproduced four gaps in the photo pipeline:

1. Freshness trusts mtime alone. A source replaced by one with an older mtime (`mv`, `cp -p`, `rsync -t`) keeps its old outputs, and a change to `MAX_IMAGE_*`, `JPEG_QUALITY` or `WEBP_QUALITY` never invalidates anything.
2. A zero-byte or corrupt output left by a killed build crashes the next build, because `is_up_to_date` opens the JPEG outside any `try`. Writes are not atomic.
3. The page-weight test hard-codes device widths and never reads `sizes`.
4. At 430 px and DPR 3 the hero needs about 1290 px, above the 1200w variant, so phones download the 346 KB JPEG.

CI builds from scratch, so 1 and 2 hit local previews and `make deploy` only. Item 4 reaches every buyer on a large phone.

## What

**PR A (items 1–2).** `sync_all_photos` loads a manifest, `build/.photo-cache.json`, which sits beside `build/public` and is never deployed. It maps each output JPEG (a path under `build/public`) to sha256(source bytes + `MAX_IMAGE_WIDTH/HEIGHT`, `JPEG_QUALITY`, `WEBP_QUALITY`, `VARIANT_WIDTHS`). `process_image` takes the manifest as an argument. The entry also records each output's size and mtime. The work is skipped only if the fingerprint matches and every recorded output is still the file that was written, so a rewrite since then (a killed build, a hand edit, a truncation) makes the entry stale. The entry is recorded only after every output is in place. Every output is encoded to `<name>.tmp` first, and only then are they all renamed into place; stray `.tmp` files under `build/public/catalog` are swept at the start of a sync. HEIC is decoded in a temporary directory outside the deployed tree. An unreadable JPEG, manifest or stamp means a rebuild, and an unreadable source fails that photo only; neither crashes the sync.

**PR B (items 3–4).** The page-weight test resolves each image's `sizes` at 390 px and 430 px, at DPR 2 and 3, and the dialog test parses `srcset`. The hero at DPR 3 gets a candidate lighter than the full JPEG, and lesson-013 states which DPR each figure assumes.

## Out of scope

- Pruning outputs of photos removed from `content/photos/` (pre-existing, recorded in the PERF-001 review).
- Caching photos in CI (it builds from scratch).
- Browser-level image tests (#99).

## Risks / open questions

- PR B: `MAX_IMAGE_WIDTH` is 1600, and variants were emitted only below the JPEG's width (`w < width`), so adding `1600` to `VARIANT_WIDTHS` alone would have emitted nothing. The decision: a variant may be as wide as the JPEG (`w <= width`), and when one is, it replaces the JPEG in `srcset`, because two candidates with the same width descriptor are invalid. The JPEG stays as `src`. Portrait photos capped at 1600 px tall (1200–1333 px wide) still offer their JPEG above 1200w. That is known and out of AC7's scope, because the hero is landscape.
- Hashing reads every source on every build: 14 photos, about 60 MB, well under a second. Hashing is still cheaper than one re-encode.
- `process_image` gains a required `cache` argument. Its only callers are `sync_all_photos` and the tests.

## Acceptance criteria

- [x] AC1: a source replaced by different content with an older mtime is rebuilt.
- [x] AC2: changing any output setting rebuilds the outputs.
- [x] AC3: an empty or corrupt JPEG, or an empty variant, is rebuilt instead of crashing the build.
- [x] AC4: every output is written under a temporary name and renamed into place. A failed write leaves the previous outputs intact and no `.tmp` behind. A killed rebuild never leaves an entry vouching for outputs it did not write.
- [x] AC5: the manifest lives outside `build/public`, a second sync rewrites nothing, and a corrupt manifest means a full rebuild.
- [x] AC6 (PR B): the page-weight test reads `sizes` at 390 and 430 px, DPR 2 and 3, on both pages. A card regressing to `100vw` fails (the DPR 3 budget and the half-screen `sizes` check).
- [x] AC7 (PR B): at 430 px and DPR 3 the hero picks a candidate lighter than the full JPEG.

## References

- Bitácora board: issue #101 (from the PERF-001 review, #20)
- Spec: `specs/archive/PERF-001-responsive-images/verification.md`
- Lessons: `docs/lessons/lesson-013-budget-page-weight-by-what-the-browser-picks.md`, `docs/lessons/lesson-016-key-build-freshness-on-content-and-settings.md`

<!-- archived 2026-09-30 — PRs: https://github.com/mlorentedev/leaving-denver/pull/110 https://github.com/mlorentedev/leaving-denver/pull/111 -->
