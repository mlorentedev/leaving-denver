---
id: "lesson-a-double-tap-is-also-the-browsers-dblclick"
type: lesson
scope: local
tags: [browser, touch, gestures, testing, javascript]
created: "2026-10-04"
source: "FEAT-016 / issue #190"
---

# Lesson: A Double-Tap Is Also the Browser's `dblclick`

## Context

FEAT-016 adds zoom to the item sheet's photo. Two taps in the same place, close in time, toggle
between fitted and enlarged; and a `dblclick` on the frame was wired to the same toggle, because
that is what a mouse does. On a phone the zoom went in and came straight back out.

## Finding

- Chrome fires a **synthesised `dblclick`** after a touch double-tap, as well as the two
  `pointerdown`/`pointerup` pairs. The page's own detector toggled the zoom in, the browser's
  `dblclick` toggled it back out, and the photo appeared not to respond at all.
- The two paths cannot be told apart by their timing: it is one gesture reaching the page twice, so
  any code that handles both has to deduplicate — or handle only one.
- It hid well. In the harness the undo arrived a few milliseconds after the second `pointerup`, so
  a test that read the transform immediately saw the zoom and passed, and one that read it a
  moment later saw the reset and failed. The same test passed or failed depending on where its
  read landed (measured 2026-10-04: the `dblclick` at 323 ms, one read at 405 ms, the next undo's
  `dblclick` arriving *after* the read that followed it).
- `touch-action: pan-y` on the frame did **not** stand in the way: both fingers of a pinch arrive
  as `pointerdown`/`pointermove` with no `pointercancel`, because `pan-y` already withholds
  pinch-zoom from the browser. That was the assumption worth spiking, and it held.

## Guard

The frame listens for pointer events only. One detector serves a mouse and a finger alike —
two presses inside the platform's own double-tap window (320 ms for touch, 500 ms for a mouse)
within 32 px — and there is no `dblclick` listener at all, so the synthesised event has nothing to
undo. `tests/test_photo_zoom_browser.py::test_a_double_tap_zooms_on_a_phone` drives a real
double-tap over CDP and fails if the toggle ever lands twice.

## Rule

When a gesture has both a pointer-level detector and a platform event for the same user action,
count the platforms first: a touch double-tap and a mouse `dblclick` are one gesture, and handling
both is handling it twice. Pick one, and if the other still arrives, let it fall through.
