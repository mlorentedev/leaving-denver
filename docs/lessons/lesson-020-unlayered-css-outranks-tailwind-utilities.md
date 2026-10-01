---
id: "lesson-unlayered-css-outranks-tailwind-utilities"
type: lesson
scope: local
tags: [css, tailwind, testing, mobile]
created: "2026-09-30"
source: "Owner report: /seller/ fields touched the phone's edges"
---

# Lesson: Unlayered CSS Outranks Tailwind Utilities

## Context

The seller page put its gutter on `<body>` as `p-4 sm:p-8`. Both classes were
in the compiled stylesheet (lesson-015's check passed), yet on a phone every
field ran edge to edge.

## Problem

`public.css` pads `<body>` for the safe-area insets in a plain rule, outside any
`@layer`. Tailwind v4 emits its utilities inside `@layer utilities`, and in the
cascade any unlayered declaration beats every layered one, whatever its
specificity. The body rule set the side padding to `env(safe-area-inset-*)`,
which is 0 on most phones. The utility was compiled, present and silently
overruled.

## Solution

The gutter moved to `<main>`, which no unlayered rule touches.
`tests/test_seller_layout_browser.py` measures the fields' distance from the
viewport edges at 320 and 390 px in headless Chrome. It failed at `[0, 0]`
before the fix.

## Takeaway

A class present in the compiled CSS can still lose. A utility on an element
that a hand-written unlayered rule also styles will lose for every property
that rule sets. Measure layout in a browser rather than inferring it from
class names.
