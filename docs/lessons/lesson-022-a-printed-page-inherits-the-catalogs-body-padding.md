---
id: "lesson-a-printed-page-inherits-the-catalogs-body-padding"
type: lesson
scope: local
tags: [css, print, testing, qr]
created: "2026-10-01"
source: "FEAT-010 (#30): the building flyer"
---

# Lesson: A Printed Page Inherits the Catalog's Body Padding

## Context

The flyer links the site's `styles.css` for its font and utilities, and has to print on one
US Letter sheet. `public.css` pads `<body>` by `6rem` at the bottom, in a plain rule, so the
sticky "Text me" bar never covers the last row of the catalog.

## Finding

On paper that padding is dead space the flyer never asked for. With it, the content box
(7.5 x 10 in after the `@page` margin) was 96 px too short and the page spilled onto a second
sheet, though every markup check passed. A utility class cannot undo it, because the rule is
unlayered and beats Tailwind's layered utilities (lesson-020).

## Guard

The flyer resets `body { padding: 0 }` in its own `<style>`, after the stylesheet link.
`tests/test_flyer_browser.py` prints the page to PDF in headless Chrome with its own `@page`
size and counts the sheets; it fails with the reset removed.
`tests/test_flyer.py` checks the QR by reading its module matrix back out of the SVG and
comparing it with `segno`'s for the literal URL. A decode of the PDF's raster by OpenCV, run
once by hand while building it, returned the same URL.

## Takeaway

Any page that reuses the catalog's stylesheet inherits its body rules. For a page meant for
paper, count the printed sheets in a browser rather than trusting the layout classes, and
assert on the QR's content rather than on its presence.
