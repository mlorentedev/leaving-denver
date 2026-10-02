---
id: "lesson-one-date-was-three-facts"
type: lesson
scope: local
tags: [data, copy, testing, yaml]
created: "2026-10-02"
source: "OPS-013 / issue #156"
---

# Lesson: One Date Was Three Facts

## Context

`seller.departure_date` fed the price windows (as offsets), the hero ("I am relocating in
November"), the flyer ("Everything must go by November 9") and the listings' month. While one date
was the day the owner left, all of those were true. When the owner split it into a household
deadline and a car deadline, each reader needed its own answer, and some had none: the hero's month
was no longer a departure, and a catalog with no furniture left would still have said "selling
furniture".

## Finding

- A derived date is true only while its premise holds. The offsets could not express "the first
  drop is already Oct 6", so the schedule is written down, one opening day per window.
- Copy that names a month or a category carries a claim about the data. The hero now has three
  variants (both, household only, car only) chosen from what is still for sale, and the flyer's
  date line only names a deadline while something under it is for sale.
- YAML reads a bare `2026-10-23` as a date object, not a string: `date.fromisoformat` raises a
  `TypeError` that names no key. The validator rejects a non-string and says which `seller.<key>`.
- Deleting items to close a deadline would have broken every bundle that names them
  (`Bundle ... names unknown items`). `published: false` already hides an item, its bundles, photos
  and share page without pretending it sold.

## Guard

`tests/test_two_deadlines.py` pins the windows, every validation failure, the countdown switch
(hidden or sold, Pending counted), the three hero variants in both languages and the flyer
line with and without the car. The runbook's close-out snippet is extracted from the runbook and run
against a copy of the real data, then the result is built.

## Rule

When a value gains a second meaning, split the field and read each reader again: a date, a month
or a category in copy is a claim, so it must come from the data it describes, not from the nearest
date. A step in a runbook that edits data is run by a test, not trusted.
