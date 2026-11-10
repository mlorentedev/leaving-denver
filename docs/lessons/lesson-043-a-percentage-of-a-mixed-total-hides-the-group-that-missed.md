# Lesson 043 — A Percentage of a Mixed Total Hides the Group That Missed

**Date:** 2026-11-09
**Tags:** [reporting, aggregation, honesty, close-out]

## What happened

The close-out aggregate (`leaving-denver retro`, OPS-018) compared what the sale realized against
what it had expected, and the first total it printed was **99 %**. That number was true, and it
was the most misleading figure of the whole sale.

Split by group it read differently: the household items recovered **65 %** of their researched
targets and **81 %** of their own reserve floors, while the car recovered exactly **100 %** of its
floor and brought in 96 % of the money. Two misses in opposite directions — six items at zero on
one side, a car at its floor on the other — summed to a number that described neither.

The same file produced a second, worse figure in the same run: **1753 %**. That one was not a
judgement call but a bug. The household group's *whole* money was being divided by the targets of
the *thirteen* items that had a target, while the numerator also held money from items that had
none (the car had no researched target and the bed listed too late to get one). Numerator and
denominator covered different populations, so the ratio was not a percentage of anything.

## Why it matters

An aggregate is the first thing anyone reads and the last thing anyone checks. Here it would have
gone into a public page as the headline of a sale, and it would have been technically accurate: no
figure was fudged, every input was real. The error was entirely in what was being compared with
what.

It also failed in the direction that hides work: 99 % says "the plan was right", when what actually
happened is "the plan was met and the price research was 35 % high on furniture". The second
sentence is the one that improves the next sale.

## Rule

- **Compare like with like, in code, not in prose.** When a ratio is computed over a subset —
  the items that have a target, the rows that have a duration — sum the numerator over that same
  subset, and keep it as its own field (`on_expected` beside `realized`). A comment saying "the
  expected value covers those items only" is not a guard.
- **Print the denominator's population beside the percentage.** The report shows `$627 (13)` —
  the sum and how many items it covers. A percentage with no visible base invites exactly this
  error.
- **Never publish one aggregate for a sale with more than one class of item.** The end page and
  the case study state the split (household against targets; the car against its own floor) and
  leave the blended total out, or name it as a blend.
- **When two classes cancel out, say so first.** The headline is not "99 % of expected"; it is
  "the car carried the result, and the furniture came in a third below its researched price".
