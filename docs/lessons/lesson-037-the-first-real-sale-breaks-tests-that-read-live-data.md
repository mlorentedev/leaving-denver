# Lesson 037 — The First Real Sale Breaks Tests That Read Live Data

**Date:** 2026-10-06
**Tags:** [testing, data, ci, catalog]

## What happened

Marking the first two real items sold (`bar-stools-pair`, `auxiliary-c-table`) turned 9 unit
tests and 7 browser tests red. The catalog itself was right: the sold cards dimmed, their
bundles went off sale, and the flyer dropped the kitchen category. The tests were wrong. They read
`data/inventory.yaml` and had been written while nothing had sold yet, so "every bundle shows
its savings", "the flyer lists all four categories" and "at least 12 items in the seller tool"
were true only on that day. Because CI gates the deploy, a sale the owner records would have
kept production on the old catalog, still showing the sold items for sale.

## Why it matters

A test that reads live data has two jobs that pull apart. A test of a mechanism (a sold item
dims, a category with nothing left disappears) needs a fixed starting state, and the real
data stops being one as soon as the first sale happens. A test of the real page (the figures
match the data) has to compute what it expects from the data. A number copied from the data
on the day the test was written is not computed from it. Both kinds read the same file, so
the failure only shows up on the first real change of state, which is also the first time
anyone needs a deploy quickly.

## Rule

1. A mechanism test that starts from the real inventory resets the state it depends on first
   (`nothing_sold()` in `tests/test_flyer.py`, the reset in the `page` fixture of
   `tests/test_item_status.py`).
2. A test of the real page derives what it expects from the data, including the statuses
   (`on_sale()` in `tests/test_build_contract.py`), and never hardcodes a count the sale
   will change.
3. A floor that guards "this test checks something" counts something sales cannot change
   (items with a discount, not discount badges shown), or follows the data exactly.
4. Before relying on a data-reading suite, run it in both states: as the data is, and with
   the state reset (the PR for this lesson ran the full suite both ways).

## Update 2026-10-16: the sample item, and the bundles

The same thing happened with the sofa (#255): 18 tests failed locally and 12 more in CI, all
because they used `sofa-sleeper`, the first item in the data, as their sample of "an item for
sale" (the seller copy, the listing tool's item menu, the item-sheet badges, the sealed-views
browser test). Earlier sales had passed because the items sold then were nobody's sample.
Taking the three bundles off the catalog did it again: the tests that read the real bundles had
none to read.

- Pick the sample by property (`status != "Sold"`, not a vehicle, not free), never by id.
- When a test needs something the real data may not have (a bundle, a sold item), build it in
  the fixture or skip with the date and the reason.
- The browser tests do not run without Chrome here, so CI is their first run and each fix costs
  about nine minutes: before `make sold`, grep `tests/` for the id and read those by eye.
- The one id that is safe to keep is the car, the last item the sale ends with.

## Related

- FEAT-006 (honest item status), FEAT-010 (flyer), issue #205 (status commands drop comments)
