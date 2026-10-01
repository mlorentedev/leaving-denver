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

Under `--virtual-time-budget`, headless Chrome stops producing frames soon after the first
paint. A `requestAnimationFrame` loop counted two or three frames in 1.5 s of virtual time.
Chrome dispatches a dialog's `close` event with a frame, so whether it arrives depends on when
the dialog closes. On Chrome 154, with a minimal page, three runs each:

| `close()` called | `close` event |
|---|---|
| in the first frame after `showModal()` | fired, every run |
| 100 ms or 1 s later | never, even after waiting 2 s more |

That is why a quick check can see the event and a test that first waits for something (the
sheet to open, history to settle) does not. `--disable-frame-rate-limit` let some frames
through, but not reliably: two to six of nineteen tests failed per run, and a step that
awaited a frame sometimes hung until the budget ran out.

## Guard

`tests/browser_harness.py` runs Chrome in real time and drives it over the DevTools protocol
on `--remote-debugging-pipe` (fds 3 and 4, messages ended by NUL), with the standard library
only. Steps poll with a deadline (`until`) instead of fixed waits, and Escape and the backdrop
are real key and mouse input (`Input.dispatchKeyEvent`, `Input.dispatchMouseEvent`). A test of
anything event-driven in `<dialog>` should not use virtual time.

A related trap: Chrome groups dialogs opened with no user activation in between, and one
Escape closes the whole group. A test that opens a stacked sheet with a synthetic `click()`
sees Escape close both; a real click, sent over CDP, keeps them apart, as a buyer's does.

A third: the first command waits for Chrome to start. On a fresh GitHub runner (main at
d32d491, 2026-10-01) it got no answer within the 30 s budget of one command: Chrome's log
showed it still starting 25 s after launch. The first test failed while every later test
passed. Only that first answer
gets a longer deadline (`STARTUP`); every other command keeps 30 s, so a hung page still fails
fast.
