---
tags: [spec, verification, tests]
created: "2026-09-30"
---

# Verification - TEST-002-computed-contrast

## Evidence

- [x] AC1: `test_text_contrast_holds_on_its_ground[en|es]`. It measures 180 text runs per page; the lowest is 4.57:1 (prices in `text-neutral-500` on the `#fbfbfb` body).
- [x] AC2: `test_checker_catches_low_contrast`, 9 cases
- [x] AC3: `test_checker_passes_readable_or_exempt_text`, 5 cases
- [x] AC4: `test_palette_and_ratio_are_calibrated`. The first attempt expected v3's 2.52:1 for `neutral-400`, but v4's `neutral-400` is #a1a1a1 (2.59:1). The calibration now uses v4's published hex values.
- [x] AC5: `test_no_text_under_12px[template|en|es]`

## Test status

- `make check` green (see PR)
- Mutation: the first `text-neutral-500` in the template became `/70`, and after a rebuild both pages failed. The template was then restored.

## Promotion candidates

- [x] Lesson: no: the calibration surprise is Tailwind v3 vs v4 palette values, recorded above; the method is in the test docstring
- [x] ADR: no: no decision changed
- [x] Pattern: no

## Archive checklist

- [ ] Independent review
- [ ] Status `archived`, folder moved, #106 closed with the PR link
