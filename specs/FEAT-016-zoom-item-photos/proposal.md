---
id: "FEAT-016-zoom-item-photos"
type: spec
status: verifying # draft | implementing | verifying | archived
created: "2026-10-04"
issue: "mlorentedev/leaving-denver#190"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-016-zoom-item-photos

## Why

The item sheet shows each photo whole, fitted to a 620 px frame inside a 42 rem sheet, and
nothing enlarges it. A buyer deciding on a sofa, a laptop or the car needs to read a scratch, a
model number or the state of a zipper, and the fitted view cannot show it. Most buyers arrive from
a listing on a phone, where the frame is barely wider than 350 px; the same catalog is read on a
desktop at 620 px. Photo stepping (#168, FEAT-016's predecessor) made every photo reachable and
none of them legible.

## What

Zoom on the photo in the item sheet, on `/` and `/es/`, for every item that has photos:

- **Enlarged and returned.** The photo is scaled about a point the buyer chose (the cursor, the
  pinch midpoint, the double-tap point) and panned by dragging, up to the point where one image
  pixel would be drawn twice.
- **Every input the buyer already has:** a `+` / `−` / `Fit` control group in the frame
  (real `<button>`s, so Tab and Enter work), a double-click, a wheel, and on a phone a pinch or a
  double-tap. Nothing new is loaded: no library, no font, no origin.
- **Real pixels, not an upscale.** While the photo is enlarged its `sizes` asks for `1600px`, so
  the browser fetches the 1200/1600 px variant instead of the 620 px one the fitted frame chose.
- **Stepping and zooming do not fight.** At fit the frame behaves exactly as it does today
  (sideways swipe and arrow keys step, a vertical drag scrolls the sheet); while enlarged the same
  drag pans the photo and the arrows still step.
- **Reset.** Changing photo, closing the sheet or pressing `Fit` returns the photo to fitted, so
  an enlargement never leaks into the next photo.

## Out of scope

- Zoom outside the item sheet: the catalog cards, the hero, the flyer and `/seller/` keep their
  current photo behaviour. The seller tool's photo list is an upload order, not a viewer.
- A full-screen viewer or a separate zoom dialog: the sheet stays the only surface.
- Cropping, rotating, downloading, comparing two photos.
- Any new measurement: zooming sends no beacon, and `/api/hit`'s event allow-list is unchanged
  (FEAT-015 owns that contract).
- Any change to the photo build: the variants and the 1600 px JPEG cap stay as they are, so zoom
  never exceeds what the pipeline already produced.

## Risks / open questions

- **`touch-action` is the whole mobile story.** The frame carries `touch-action: pan-y` so the
  sheet can be scrolled over the photo and sideways swipes reach the gallery. A spike
  (2026-10-04, `tests` harness, headless Chrome) confirmed that both pointers of a two-finger
  pinch arrive as `pointerdown`/`pointermove` under `pan-y` with no `pointercancel`, so pinch needs
  no change to it. Panning *vertically* while enlarged is the one case `pan-y` withholds (the
  browser scrolls the sheet and cancels the pointer), so the frame switches to `touch-action: none`
  **while enlarged only**, and back at fit. Verified behaviour at fit must not regress: the swipe
  and the vertical scroll are covered by the existing `tests/test_photo_gallery_browser.py`.
- **The wheel is also the sheet's scroll.** On a desktop the wheel over the photo scrolls the
  sheet today. Taking it unconditionally would strand a buyer mid-sheet. Decision: the wheel zooms
  **only while the photo is already enlarged**; at fit it scrolls as before, and Ctrl/⌘+wheel zooms
  from fit (suppressing the browser's own page zoom, which is what the buyer meant over a photo).
  The buttons and the double-click are the discoverable entry points.
- **Zoom needs pixels that exist.** The largest candidate is the 1600 px WebP (or the JPEG at its
  own width, itself capped at 1600 px). The scale stops at the first point where the source would
  be interpolated — `largest / displayed`, clamped to `[2, 5]` — so the `+` button never promises
  detail that is not there; a 1600 px photo in a 620 px frame stops at 2.58×.
- **The wheel is testable, but lazily.** CDP delivers `Input.dispatchMouseEvent type=mouseWheel`
  to the page (spike above), but the harness reads events only on the next round trip, so a test
  must make a round trip (`browser.run("return 0;")`, as `Page.errors()` already does) before it
  asserts on the log.
- **A zoomed photo is a finger trap if panning has edges.** The pan is clamped so no gap opens at
  the frame's edge; a swipe past the edge while enlarged does not step to the next photo (that is
  what `Fit` is for). Accepted: it is what every photo viewer does, and it is named in the test.
- **No accessibility regression.** The zoom controls are buttons with localized labels in the
  frame's existing tab order; the arrow keys keep stepping (the zoom deliberately takes no
  character keys, which collide with the browser's own zoom shortcuts and with layouts where
  `+`/`−` need a modifier).

## Acceptance criteria

- [ ] **AC1: enlarge and return.** With the sheet open on an item, `+` enlarges the photo and
  `Fit` returns it to fitted; the scale is between 1 and the photo's source-limited maximum, and
  the photo is never scaled below 1.
- [ ] **AC2: the fitted frame is unchanged.** At fit, a sideways swipe still steps to the next
  photo, a vertical drag still scrolls the sheet, the arrow keys still step, and `touch-action`
  is `pan-y`. While enlarged, a sideways drag pans the photo instead of stepping and the arrow
  keys still step.
- [ ] **AC3: the four inputs.** A double-click (desktop) and a double-tap (touch) toggle between
  fitted and enlarged about the point that was hit; a wheel enlarges while already enlarged and
  scrolls the sheet at fit; Ctrl+wheel enlarges from fit; a two-finger pinch scales by the ratio
  of the fingers' distance, anchored at their midpoint.
- [ ] **AC4: zoom at the point, pan without gaps.** Enlarging about a point keeps that point
  under the pointer; a pan is clamped so the photo always covers the frame while enlarged.
- [ ] **AC5: reset.** Changing photo (arrow, swipe, thumbnail, arrow key) and closing the sheet
  both return the photo to fitted.
- [ ] **AC6: real pixels.** While enlarged the main image's `sizes` asks for `1600px`, so the
  candidate the browser resolves is wider than the one the fitted frame resolved.
- [ ] **AC7: no new surface.** No new script origin, no new inline event handler attribute, no
  `unsafe-inline`; the emitted CSP hash list still matches the emitted pages (ADR-010), the page
  logs no console error, and no captured beacon payload changes (ADR-011).

## References

- Issue #190 (the work gate); #168 for the stepping this must not regress
- ADR-010 (hash-pinned CSP on the public pages), ADR-011 (the beacon contract), ADR-002 (the phone)
- PERF-001 (the variant widths this relies on), lesson-014 (headless Chrome drives the pointer),
  lesson-017 (real time, not virtual time, in the browser harness)
- lesson-024 (an inline script under a hash-pinned CSP)
