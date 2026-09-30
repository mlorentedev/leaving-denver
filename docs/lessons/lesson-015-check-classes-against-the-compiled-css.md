---
id: "lesson-check-classes-against-the-compiled-css"
type: lesson
scope: local
tags: [testing, css, tailwind]
created: "2026-09-30"
source: "BUG-009 (#103), raised by the independent BUG-003 review"
---

# Lesson: Check Classes Against the Compiled CSS

## Context

Tailwind v4 scans the templates and emits a rule for every class it recognises.

## Finding

An unrecognised class, whether a typo such as `text-netural-500` or a utility renamed between versions, produces no rule and no warning. The build is green and the page ships unstyled. Checking a handful of known utilities in the output proves only those, and matching minified bytes breaks on harmless reordering.

## Guard

`tests/test_class_coverage.py` compares every class token a page can use against the class selectors of the stylesheet that ships with it. It unescapes selectors (`.md\:flex` is `md:flex`) and fails on any token with no rule. Where tokens come from matters more than the comparison:
- Jinja branches and macro arguments are only visible once rendered. The test renders both locales with the data forced into every status (an item Sold, one Pending, the vehicle Sold or Pending), because a Sold-only class never appears in a page where nothing is sold.
- Script-built classes are read from the source: `className` / `classList` literals, `${...}` ternary branches, and registered class maps such as `STATUS_PILL`. A lookup into an unregistered map fails, so a new map cannot hide its classes.
- Script hooks with no rule (`item-card`, `filter-btn`) are declared by name, so the exemption list is visible and short.

Before trusting a guard like this, inject a typo in each context and see it reported. Every context that is not caught is a blind spot.
