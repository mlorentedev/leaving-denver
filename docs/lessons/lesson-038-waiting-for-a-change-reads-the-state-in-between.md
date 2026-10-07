# Lesson 038 — Waiting for "Changed" Reads the State In Between

**Date:** 2026-10-06
**Tags:** [testing, browser, flaky, ci, race]

## What happened

`test_the_enlarged_photo_asks_for_a_wider_variant` failed once in CI on a diff that touched
nothing in the photo pipeline (`assert 0 > 800`, issue #202) and passed on re-run. It waited for
`currentSrc` to differ from the fitted photo's, then read the width of the variant out of it. A
`currentSrc` that differs is not a `currentSrc` that is a variant: while the browser switches
candidates it can read as something no variant matches, and the test took that moment as "done".
The failed job also skipped the deploy (lesson 034).

## Why it matters

"It changed" and "it settled on the value I assert about" are different conditions, and only the
first is cheap to write. The gap between them is a few milliseconds on a developer's machine and
a failed job on a loaded runner: 150 local runs, several under 16 busy loops, never hit it. A race
that rare cannot be found by looping the test, so the fix has to be argued from the code and then
made reproducible on purpose. Here the test replaces `currentSrc` with a getter that reads empty
for 300 ms after the zoom click; the old wait fails that every time with the exact CI message.

## Rule

1. Wait for the condition the assertion needs (`variant > fitted`), never for a proxy for it
   (`!== before`). `wait_for_variant` in `tests/test_photo_zoom_browser.py` is the shape.
2. The harness's `until` swallows its own timeout, so return what the wait last saw and assert
   on it; the failure then names the value, not a timeout.
3. When a flake cannot be reproduced by repetition, widen the window under test control (a
   getter that lies for a while) and keep that case in the suite as a parameter.
4. A fixed test must still fail with the feature broken: the mutation check for this one makes
   the zoom ask for the narrowest candidate and expects `480 > 800`.

## Related

- Issue #202, lesson 034 (a skipped deploy is not a failed one), issues #195 and #185 (same family)
