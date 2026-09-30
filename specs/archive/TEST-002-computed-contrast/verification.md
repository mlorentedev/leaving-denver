---
tags: [spec, verification, tests]
created: "2026-09-30"
---

# Verification - TEST-002-computed-contrast

## Evidence

- [x] AC1: `test_text_contrast_holds_on_its_ground[en|es]`. It measures 180 text runs per page; the lowest is 4.57:1 (prices in `text-neutral-500` on the `#fbfbfb` body).
- [x] AC2: `test_checker_catches_low_contrast` (11 cases), `test_script_fragments_are_parsed_as_markup`, `test_breakpoint_guard_sees_every_colour_form` (3)
- [x] AC3: `test_checker_passes_readable_or_exempt_text`, 6 cases
- [x] AC4: `test_palette_and_ratio_are_calibrated`. The first attempt expected v3's 2.52:1 for `neutral-400`, but v4's `neutral-400` is #a1a1a1 (2.59:1). The calibration now uses v4's published hex values.
- [x] AC5: `test_no_text_under_12px[template|en|es]`

## Test status

- `make check` green (see PR)
- Mutation: the first `text-neutral-500` in the template became `/70`, and after a rebuild both pages failed. The template was then restored.

## Review findings (CodeRabbit on 28b4456)

| Finding | Disposition |
|---|---|
| `opacity-*` faded only the text, not its ground; white on a 50% black read 5.28:1, really 3.98:1 | **Applied.** Each group maps painted colours to the screen as k·c + offset, exact for nested groups on opaque grounds. Two failing cases added; comparing against the unmapped ground fails 2 tests. |
| Script HTML fragments were wrapped in `class="…"`, so the spec bullet went unchecked | **Applied.** Fragments are parsed as markup with `${…}` replaced; the test requires the spec bullet sample. Treating fragments as classes fails 2 tests. |
| The breakpoint guard missed arbitrary hex and `opacity-*` | **Applied.** The guard covers `(text|bg)-[#…]` and `opacity-N`, with a test for each form. |

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? no: the calibration surprise is Tailwind v3 vs v4 palette values, recorded above; the method is in the test docstring
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: no decision changed
- [x] Cross-project pattern for `00_meta/patterns/`? no: the contrast check is specific to this site's palette

## Archive checklist

- [x] Independent review: the launcher review (`dotf spec review`) was waived by the owner on 2026-09-30, see `review_waived_reason` in proposal.md. The only review on record is CodeRabbit on #109; no independent reviewer-subagent pass ran.
- [x] Status `archived`, folder moved, #106 closed with the PR link
