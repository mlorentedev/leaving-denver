---
id: "lesson-virtual-time-starves-dialog-close-events"
type: lesson
scope: local
tags: [testing, browser, dialog]
created: "2026-09-30"
source: "TEST-001 (#99): browser tests for the sheets' close paths"
---

# Lesson: Virtual Time Starves Dialog Close Events

## Context

The Share button's browser tests ran headless Chrome with `--dump-dom --virtual-time-budget`,
which is quick and needs no protocol client. Reusing that harness for the sheets, every close
path closed the `<dialog>` but left its history entry behind: the page's `close` listener,
which calls `history.back()`, never ran. Back itself worked, because it does not go through
that event.

## Finding

Under `--virtual-time-budget`, headless Chrome stops producing frames after the first paint.
A `requestAnimationFrame` loop counted two frames in 1.5 s of virtual time. Chrome dispatches
a dialog's `close` event with a frame, so it never arrived, for `show()` and `showModal()`
alike. `--disable-frame-rate-limit` let some frames through, but not reliably: two to six of
nineteen tests failed per run, and a step that awaited a frame sometimes hung until the
budget ran out.

## Guard

`tests/browser_harness.py` runs Chrome in real time and drives it over the DevTools protocol
on `--remote-debugging-pipe` (fds 3 and 4, messages ended by NUL), with the standard library
only. Steps poll with a deadline (`until`) instead of fixed waits, and Escape and the backdrop
are real key and mouse input (`Input.dispatchKeyEvent`, `Input.dispatchMouseEvent`). A test of
anything event-driven in `<dialog>` should not use virtual time.
