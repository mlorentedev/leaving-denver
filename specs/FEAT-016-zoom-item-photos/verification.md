---
tags: [spec, verification, templates]
created: "2026-10-04"
---

# Verification - FEAT-016-zoom-item-photos

## Evidence

Every acceptance criterion maps to a test that drives a real browser over CDP
(`tests/browser_harness.py`) and reads what the browser paints — the computed transform matrix,
the `sizes` the image resolves, `touch-action`, and the photo the strip marks as shown. The
verification commands in `features.json` were run one by one; each exits 0 with a non-zero number
of tests selected (4, 6, 6, 2, 2, 1, 6).

- [x] AC1 -> `tests/test_photo_zoom_browser.py::test_the_controls_are_labelled_buttons` (both
  locales), `::test_a_button_enlarges_and_fit_returns`, `::test_the_scale_never_leaves_its_range`
  (the scale must *reach* the ceiling, not merely stay under it — see the review finding below)
- [x] AC2 -> `::test_at_fit_the_frame_keeps_its_swipe_and_its_scroll` (touch-action `pan-y`, a
  swipe still steps), `::test_an_enlarged_photo_pans_instead_of_stepping` (the drag pans, the
  arrows still step), and the untouched `tests/test_photo_gallery_browser.py` (7 tests, all green)
- [x] AC3 -> `::test_a_double_click_toggles_in_and_out`, `::test_a_double_tap_zooms_on_a_phone`
  (both locales), `::test_the_wheel_scrolls_at_fit_and_zooms_when_enlarged`,
  `::test_ctrl_wheel_enlarges_from_fit_and_leaves_the_page_zoom_alone`,
  `::test_a_pinch_scales_by_the_spread`
- [x] AC4 -> `::test_enlarging_about_a_point_keeps_it_under_the_pointer` (the same image pixel
  under the pointer within 2 px), `::test_a_pan_cannot_open_a_gap`,
  `::test_a_resize_re_clamps_the_pan` (a rotation or a window resize re-clamps the pan, so no
  gap opens against a room the transform no longer fits)
- [x] AC5 -> `::test_changing_the_photo_resets_the_zoom` (arrow button and arrow key),
  `::test_closing_and_reopening_the_sheet_starts_fitted`
- [x] AC6 -> `::test_the_enlarged_photo_asks_for_a_wider_variant` (`sizes` becomes `1600px` and
  `currentSrc` moves to a wider candidate); `tests/test_responsive_images.py` pins that the
  enlarged `sizes` asks for at least 1200 px
- [x] AC7 -> `::test_no_gesture_ever_throws` (a window `error` collector around a double-click, a
  wheel, a pinch and a drag), plus the untouched `tests/test_public_csp.py` (the emitted hashes
  still match the emitted pages) and `tests/test_class_coverage.py`

## Test status

- Test suite: `make check` -> **1308 passed, 8 skipped** (3:58), lint and format clean
- End-of-sale mode (`seller.sale_over: true`, the switch on, `make check`) -> **1066 passed, 250
  skipped**. The 18 new tests are listed in `conftest.CATALOG_TESTS` and are among the 250: the
  catalog is not built then, and `test_a_double_tap_zooms_on_a_phone` joins
  `SKIPPED_DESPITE_ITS_NAME` because its name says "phone" (a phone screen, not the seller's
  number)
- Manual smoke test: the built page driven over CDP at a 390x844 mobile viewport, screenshots
  before and after a double-tap. At fit the whole car is shown inside the frame with the controls
  at its bottom left; at 2x the photo is enlarged about the point that was tapped, the controls
  and the counter stay legible over it, and `Fit` returns the frame to an identical picture
- No regressions in the existing suite: **yes** — the 7 photo-gallery tests (the swipe, the arrow
  keys, the mouse press released off the photo) pass unchanged

## Decisions made during implementation

- **One tap detector, no `dblclick` listener.** Chrome fires a synthesised `dblclick` after a
  touch double-tap, so a page that also handles `dblclick` toggles twice and the photo appears not
  to respond. The frame listens for pointer events only, with the platform's own double-tap
  window per pointer type (320 ms touch, 500 ms mouse). Written up as lesson-033.
- **The wheel zooms only once the photo is enlarged**, plus Ctrl/⌘ from fit. At fit the wheel
  stays the sheet's scroll: taking it there would strand a buyer reading the sheet on a desktop
  with the cursor over the photo. The buttons and the double-click are the discoverable ways in.
- **`touch-action` switches to `none` only while enlarged**, so the sheet can still be scrolled by
  dragging over the photo at fit, and a pan cannot be stolen by the browser's scroll while zoomed.
  A spike confirmed both pointers of a pinch already arrive under `pan-y` (no `pointercancel`), so
  the pinch needed no change to it.
- **The scale stops at the photo's own pixels** — `widest / displayed`, clamped to `[2, 5]` — so
  the `+` control never promises detail the 1600 px build does not hold.
- **pr-agent found that ceiling dead on the first review of PR #192** (fixed on the PR):
  `Math.max(0, [...srcset.matchAll(/(\d+)w/g)].map(Number))` passes the *array* to `Math.max`, so it
  was `NaN` and every photo stopped at the `2` fallback — a 1600 px source in a 580 px frame wanted
  2.76. The spreading operator was missing. The test that should have caught it asserted only
  `scale <= ceiling`, and it computed the ceiling correctly itself, so a page that was *more*
  conservative than the test's bound passed. It now asserts the control reaches the ceiling
  (`scale == approx(ceiling)`, 2.76 on the car's cover), which fails on the bug reintroduced
  (checked: `2 == 2.7586 ± 0.01`). Fix: spread the mapped widths.
- **pr-agent's second finding on PR #192** (theoretical, low): nothing re-clamped the pan when the
  frame's size changed, so rotating a phone left the photo's edge inside the frame until the next
  pan. Applied, not just disclosed: a `ResizeObserver` on the frame re-runs `zoomTo(scale)`, which
  re-caps the scale and re-clamps the shift. `::test_a_resize_re_clamps_the_pan` shrinks the
  viewport under an enlarged, panned photo and fails without the observer (`432.5 <= 320.75 + 1` —
  a 112 px gap), then passes with it.
- **The pan clamps to the frame's content box**, not to its outer box: the `p-2` padding is the
  mat the photo already sits inside at fit.
- **A `const style = getComputedStyle(…)` in this script fails `test_public_csp.py`'s
  `\sstyle\s*=` search**, which means to catch a `style="…"` attribute. The local was renamed
  (`box`); the guard was left as it is rather than narrowed inside a feature PR, and the false
  positive is filed as #191.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive`
refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a
`00_meta/` path is looked up in the vault.

- [x] Lesson for the repo's `docs/lessons/`? yes: `docs/lessons/lesson-033-a-double-tap-is-also-the-browsers-dblclick.md` (a touch double-tap is also the browser's `dblclick`; a page that handles both undoes its own zoom). Numbered 033 because #186 holds 031 and 032
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: the zoom is UI inside the existing sheet. It adds no origin, no dependency and no contract; ADR-010 (the hash-pinned CSP) and ADR-002 (nothing new is sent) already cover what it touches, and both tests still pass unchanged
- [ ] New pattern candidate for `00_meta/patterns/`? no: nothing here recurs across projects. `pattern-architecture` covers the layering this keeps, and the gesture lesson is repo-and-platform specific

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/FEAT-016-zoom-item-photos/` -> `specs/archive/FEAT-016-zoom-item-photos/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
