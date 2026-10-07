# Lesson 039 — The First Tap Pays for the Cold Start

**Date:** 2026-10-06
**Tags:** [performance, inp, frontend, measurement]

## What happened

Cloudflare Web Analytics reported INP "Needs Improvement" (360 ms) on the item card's cover
image (issue #213). The guess in the ticket was a handler that does too much synchronous work
(gallery, zoom setup, beacon). Measuring first showed otherwise. On a 390 px mobile profile
with 4x CPU throttling, the first tap on a fresh page took a median 140 ms (handler ~90 ms)
while the second and later taps took ~48 ms (handler ~20 ms). The warm handler was already
cheap; the first call was not, and two cold-start costs made up most of the gap:

- `Number.prototype.toLocaleString` loads the locale data on its first call: ~35 ms for the
  sheet's price line, paid inside the click.
- `dialog.showModal()` on a never-opened sheet runs the sheet subtree's first style pass:
  ~40 ms cold against ~15 ms warm.

The beacon (`sendBeacon`, 0.4-6 ms) and the neighbour-photo preloads (2-6 ms) were small
enough that deferring them would have bought nothing and changed when `view_item` is sent.

## Why it matters

INP is the worst interaction of a visit, and for a catalog people open once or twice the
worst one is usually the first. Deferring work out of the handler (`requestAnimationFrame` plus
`setTimeout`) is the standard answer, but it only helps when the work is warm and avoidable. Cold
one-time costs belong somewhere else: before the first tap, while the page is idle.

## Rule

1. Measure the first interaction on a fresh page separately from later ones: the warm path hides
   the cold one. Read Event Timing (`PerformanceObserver` with `type: 'event'`, entries with an
   `interactionId`) under `Emulation.setCPUThrottlingRate`, not a trace of a second tap.
2. Time the suspects cold, one fresh page each, before changing anything. A section-by-section
   `performance.now()` on a copy of the built page is enough; the guess was wrong here.
3. Pay one-time costs (formatter, first style pass of a hidden sheet) on `load` + idle, not in
   the handler. `requestIdleCallback` is absent in Safari, so fall back to a timer.
4. Do not assert timings in CI. Assert what the warm-up does (it ran before any tap) and that
   it leaves no trace (`tests/test_sheet_warmup_browser.py`), and mutation-check it by removing
   the trigger.

## Related

- Issue #213 and PR #221; `src/leaving_denver/templates/index.html` (`warmSheet`).
- The sheet's `backdrop-filter: blur(4px)` cost a further ~25 ms of presentation delay on the
  first open (software raster, 4x throttle). The owner chose to drop it (2026-10-06): the
  backdrop is a plain dark overlay now.
