# Case study: emptying an apartment in 45 days

Sixteen items, a two-bedroom apartment in Denver Tech Center, one departure date. The catalog
opened on 2026-09-25 and the last item left on 2026-11-09: **45 days**. Nothing went to the
dumpster.

| | |
|---|---|
| Items placed | **16 of 16** |
| Sold | **10** |
| Given away | **6** |
| Left behind or thrown away | **0** |
| Recovered against the asking prices | **86 %** |
| Median days to sell, household items | **15 days** |

The figures come from `make retro`, which adds up the targets, the reserve floors and the realized
price of every sale from the encrypted seller record. Absolute amounts are not published; the
percentages and the days are, because they are the part that transfers to another move. Run in
the repository, on the day this page was last touched, it is the authority on every number here.

## What the plan said, and what happened

The preparation was a written price plan, not intuition: each household item carried a researched
target (what it should fetch, from a pricing pass on 2026-09-25) and a reserve floor (the price
below which it would be given away rather than sold). The household deadline was 2026-10-23 and
the car's was 2026-11-09.

Against those targets the household items recovered **65 %**. Against their own reserve floors they
recovered **81 %** — below the floors in aggregate, because six items ended at zero. The car
recovered **88 %** of its asking price and **exactly 100 %** of its floor.

That is the honest reading of the sale, and it is the interesting one:

- **The plan was met, the price research was optimistic.** Everything left the apartment by its
  deadline and nothing was abandoned, which is what the plan was for. But furniture sold for about
  two thirds of the researched expectation. A used sofa, a bed, a desk and a chair in a city with a
  constant churn of departing renters are worth less than a listing price suggests, and each week
  they sit they are worth less still.
- **The car carried the result, and its floor was the only honest number in its listing.** It sold
  on the last day of its window, at the reserve floor set for instant offers. The asking price was
  a wish; the floor was the expectation. On the next sale, the floor would be the number in the
  listing and the wishing would stop.
- **The giveaways were the plan working, not the plan failing.** Four of the six items that left
  without money went in the final days, inside the giveaway window that had been written down in
  advance. Choosing to give something away on a fixed date is a decision; discovering on moving day
  that it must be abandoned is not. Six of sixteen is a normal rate for furniture at this end of
  its life.

## What made the difference

- **A deadline per class of item, written down.** Household items by 2026-10-23, the car by
  2026-11-09. Two dates, two campaigns, no negotiation with a single date that everything slides
  past.
- **A price schedule rather than renegotiation.** One drop, then the reserve floors, then a
  giveaway window, each opening on a date fixed in advance. Deciding the drop dates in September
  meant not arguing with each buyer in October.
- **One record of what was true.** Every item's status, its asking price and its realized price
  lived in one place that both the public page and the seller's tools read, so what buyers saw
  and what the plan said could not drift apart.

## What was built for it

A static bilingual catalog generated from a single YAML inventory, with a photo pipeline that
strips location metadata, share pages per item for each marketplace, a printable building flyer
with its own QR code, a private seller panel for repricing and posting, and a decommission path
that ends the sale on schedule and leaves one page behind. The repository, its decisions and its
44 lessons are public: see the [README](../README.md).

## If you are doing this yourself

The method is not a secret and the code is forkable. What it buys is the unglamorous part: one
inventory, one price plan with fixed dates, one page that buyers can check at 11 pm, and an end
that happens on time. Write to the address on [the site](https://leaving-denver.pages.dev) if you
want it built for your move.
