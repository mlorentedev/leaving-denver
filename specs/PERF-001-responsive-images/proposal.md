---
id: "PERF-001-responsive-images"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-29"
issue: "mlorentedev/leaving-denver#20"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# PERF-001-responsive-images

> **Naming**: file lives at `<repo>/specs/PERF-001-responsive-images/proposal.md`. `PERF-001-responsive-images` is `AREA-NNN-slug` (e.g. `TOOL-001-secret-drift`).

## Why

<!-- from issue #20: PERF-001: Responsive images and lighter page -->

The live catalog downloads 5.1 MB of photos (13 images, measured 2026-09-29) because every card, the vehicle hero and even the 48 px bundle thumbnails load the full 1500–1600 px JPEG. Buyers open the link from Facebook, Nextdoor and SMS on phones, often on mobile data inside in-app browsers, where that weight is the difference between a page that shows items and one that is abandoned.

## What

Each synced photo also ships as WebP variants 480/800/1200 px wide (never upscaled), next to the canonical JPEG. Every catalog `<img>` (cards, vehicle hero, bundle-sheet thumbnails, item dialog) carries `srcset`, `sizes`, `width` and `height`, so the browser picks the smallest adequate file and reserves layout space. Photos honour their EXIF orientation before metadata is dropped. The vehicle hero is fetched with high priority and not lazy-loaded. Re-running the build skips photos whose outputs are newer than their source.

## Out of scope

- Fonts (self-hosting or the system stack): a follow-up PR under the same issue.
- Changing `images:` in `data/inventory.yaml`, the canonical JPEG size, or the private poster assistant (it keeps full JPEGs for posting).
- Per-item share pages and OG images (#14).

## Risks / open questions

- `images` is a public template/JSON contract (lesson-012): variants are added as a parallel `photos` field; `images` stays as is.
- WebP metadata: variants are written from a fresh RGB buffer, no `exif=` argument; a test asserts no EXIF in any output.
- Build time: 4–5 MB sources × 4 outputs; incremental skip keeps local rebuilds fast. CI builds from scratch on every run (cache out of scope).

## Acceptance criteria

- [ ] AC1: a photo wider than 480/800/1200 px produces WebP variants at exactly those widths; a narrower one produces none; no output carries EXIF, and an EXIF-rotated source comes out upright.
- [ ] AC2: every catalog `<img>` in EN and ES has `srcset`, `sizes`, `width` and `height`, and every `srcset` URL is a built file.
- [ ] AC3: the vehicle hero has `fetchpriority="high"` and no `loading="lazy"`; the item dialog sets `srcset` on its main photo and thumbnails.
- [ ] AC4: a second build does not rewrite up-to-date photo outputs.
- [ ] AC5: the covers a 2-column phone at DPR 2 would pick weigh less than a third of the full JPEG covers.

## References

- Bitácora board: issue #20
- Lessons: `docs/lessons/lesson-012-template-contexts-are-public-data-contracts.md`
- ADR: `docs/adr/adr-003-render-the-catalog-from-data-with-jinja2.md`
