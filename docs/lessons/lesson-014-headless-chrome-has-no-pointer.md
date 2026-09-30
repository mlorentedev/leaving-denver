---
id: "lesson-headless-chrome-has-no-pointer"
type: lesson
scope: local
tags: [testing, browser, accessibility]
created: "2026-09-30"
source: "FEAT-003 PR 3 (#15): desktop contact sheet behind (hover: hover) and (pointer: fine)"
---

# Lesson: Headless Chrome Has No Pointer

## Context

The desktop contact sheet only takes over a text link when
`matchMedia('(hover: hover) and (pointer: fine)')` matches. Verifying it over CDP, the page
never saw a desktop: every click still went to `sms:`.

## Finding

Headless Chrome reports `(pointer: none)` and `(hover: none)`. So did a headed Chrome started
from the agent sandbox, which cannot see the input devices. `Emulation.setEmulatedMedia`
accepts `pointer`/`hover` features without error and changes nothing, and
`--blink-settings=primaryPointerType=…` did not either. Touch emulation
(`Emulation.setTouchEmulationEnabled`) does flip the page to `(pointer: coarse)`, so only the
mobile side can be reproduced faithfully.

## Guard

The CDP run stubs `window.matchMedia` for that one query with
`Page.addScriptToEvaluateOnNewDocument` (before the page script caches it), drives the desktop
flow with real mouse events, then removes the stub and checks the touch-emulated page leaves
`sms:` alone. The query string itself is pinned by `tests/test_desktop_contact.py`; a real
mouse check on a desktop browser remains the one manual step.
