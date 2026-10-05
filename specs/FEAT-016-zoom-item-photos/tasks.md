---
tags: [spec, tasks, templates]
created: "2026-10-04"
---

# Tasks - FEAT-016-zoom-item-photos

> TDD order. One task = one focused commit. Tick as you go. Frozen now that the spec is being
> implemented; reordering needs a proposal edit.

## Setup

- [x] Branch created from `origin/main`: `feat/zoom-item-photos`
- [x] `proposal.md` complete, acceptance criteria testable
- [x] No open questions left in `proposal.md` "Risks / open questions" (the pinch-under-`pan-y`
      and CDP-wheel assumptions were spiked on 2026-10-04 before this file froze)

## Implementation

> The tests come first and drive real input over the CDP harness (`tests/browser_harness.py`),
> never a string in the page. The observable is what the browser paints: the computed `transform`
> matrix, the resolved `sizes`, `touch-action`, and the photo the gallery shows.

- [x] [P] [AC1] Failing tests: the controls exist and are labelled; `+` enlarges, `−` shrinks,
      `Fit` returns; the scale stays within `[1, max]`
- [x] [AC1] Locale keys (`zoom_controls`, `zoom_in`, `zoom_out`, `zoom_fit`) in `en`/`es`, and
      the control group in the frame
- [x] [AC1] The zoom state and `setScale`/`paint`/`resetZoom` (transform, `sizes` while enlarged)
- [x] [AC4] Enlarge about the point that was hit; clamp the pan so no gap opens
- [x] [AC6] `sizes="1600px"` while enlarged, so a wider variant resolves
- [x] [AC3] Wheel: zooms while already enlarged, Ctrl/⌘+wheel from fit, otherwise the sheet
      scrolls as before
- [x] [AC3] Double-click and double-tap toggle about the point that was hit
- [x] [AC3] Pinch: scale by the ratio of the fingers' spread, anchored at their midpoint
- [x] [AC2] Drag pans while enlarged; `touch-action: none` while enlarged and `pan-y` at fit;
      the swipe and the arrow keys keep stepping at fit
- [x] [AC5] `showPhoto` resets, so a photo change and a reopen start fitted
- [x] [AC7] No new handler attribute, no new origin: the CSP hash list still matches the pages
- [x] Refactor for clarity: the gesture block split into named functions, each under 40 lines

## Closing

- [x] Every acceptance criterion covered by at least one test
- [x] Every acceptance criterion has a `features.json` entry with a non-vacuous command
- [x] No unrelated changes in the diff
- [x] `make check` green (1290+ passed) and the browser suite green
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder

## Machine-readable features

See `features.json` beside this file.
