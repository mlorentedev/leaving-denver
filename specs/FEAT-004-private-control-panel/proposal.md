---
id: "FEAT-004-private-control-panel"
type: spec
status: implementing # draft | implementing | verifying | archived
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#16"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-004: Private control panel for floors, targets and listing tracking

## Why

<!-- from issue #16: FEAT-004: Private control panel for floors, targets and listing tracking -->

The sale runs six weeks across four marketplaces. What the owner has to decide each day
is spread over four places: asking prices in `data/inventory.yaml`, floors in the encrypted
file, the drop windows in `leaving-denver drops`, and a memory of what was posted where and
when Facebook needs renewing. Nothing records what an item actually sold for or when the
price moved, so afterwards nobody can say whether a drop worked. One local page that joins
those, plus a private place to record the events, closes both gaps.

## What

`make panel` writes `build/private/panel.html`: one row per item with asking price, target,
floor, status, days listed, channels posted, Facebook renew due, next drop date and the
suggested price at that drop. It is a local file, never part of `build/public/`.

Three commands record what happens, all into `data/private.sops.yaml` through `sops set`
(values on stdin, never argv; the owner never decrypts the file by hand):

- `make post ID=<item> CHANNEL=<channel>` appends today's date to that channel's posting
  history (a renewal is another post);
- `make reprice ID=<item> PRICE=<usd>` appends `{at, price}` to the item's price log;
- `make sold ID=<item> PRICE=<usd>` (existing) now records `{price, at}` as the sale and
  lists the channels that item was posted on as the takedown checklist.

Where the data lives, in `data/private.sops.yaml`:

```yaml
floors:   {<item-id>: <usd>}              # existing
targets:  {<item-id>: <usd>}              # new: researched expected close, owner-filled (make secrets)
sales:    {<item-id>: {price: <usd>, at: <date>}}   # a bare number (the old shape) still reads
tracking:
  <item-id>:
    channels:  {<channel>: [<date>, ...]}   # facebook, craigslist, offerup, nextdoor, activebuilding
    price_log: [{at: <date>, price: <usd>}]
```

Decisions:

- Tracking is private, not public. `listed_at` and the channel list would be harmless on their
  own, but days listed with no sale tells a buyer the seller is getting desperate (the same
  leverage the playbook keeps out of public view for drop timing). The public repo also gets a
  commit, a review and a deploy for every post, while the private file is one command.
  `listed_at` is derived (the earliest posting date), never typed.
- Output is HTML in `build/private/`, not a terminal table: 10 columns by 17 items does not
  fit a terminal. `build/private/` is git-ignored, not in `pages_build_output_dir`, scanned
  by `verify_security_guarantees` and served on loopback only by `make serve`.
- Asking price is `recommended_list_price`: that is what the public build publishes and what
  `drops` starts from.
- Drop tiers (list, drop, floor) come from one function that `drops` and the panel share.
  The panel's next step is the first tier strictly below the current asking price, dated at
  the start of its window: tier "drop" at the first drop window, tier "floor" at the clear
  floors window. The second drop window has no tier of its own in `drops`, so it is not a
  step here.
- Facebook renews every 7 days; the per-channel rule is a small map, not a scheduler.

## Out of scope

- A server, a login or any hosted view. The panel is a file on the owner's disk.
- Editing `data/inventory.yaml` from `reprice`: the asking price is still edited by hand
  (it needs review and a deploy). The panel warns when the log and the asking price disagree.
- Reminders or notifications (Craigslist 48 hour bump is the existing n8n workflow).
- Filling in the real targets or tracking history: those are owner data, entered with
  `make secrets` and the commands above.

## Risks / open questions

- The real file has no `targets:` yet, so the Target column shows a dash until the owner adds
  them.
- `sops set` rewrites one key at a time; two commands at once could race. One owner, one
  terminal: accepted.

## Acceptance criteria

- [ ] AC1: For every item in the inventory the panel has a row with asking price, target,
  floor, status, days listed, channels posted, renew due, next drop date and suggested
  price; a field the private data does not hold is empty, never a crash or a guess.
- [ ] AC2: `leaving-denver drops` and the panel compute the price tiers with the same
  function, and `drops` prints the same table as before.
- [ ] AC3: The next drop is the first tier below the current asking price with its window's
  start date, flagged overdue once that date has passed, and empty for an item at its floor,
  free with purchase, or no longer Available.
- [ ] AC4: Renew due is seven days after the latest Facebook posting and is flagged when it
  is today or past; days listed counts from the earliest posting and stops at the sale date.
- [ ] AC5: `post`, `reprice` and `sold` write only to `data/private.sops.yaml`, through
  `sops set` with the value on stdin, and leave `data/inventory.yaml` free of prices, dates
  and channels; a failed write changes nothing.
- [ ] AC6: `sold` records the sale price and date, and prints take-down steps for the
  channels the item was posted on (the full checklist when none is recorded).
- [ ] AC7: The panel is written only outside `build/public/`; the build fails if a panel
  file is found under it, and no private fixture value or panel file appears in a public
  build made while the private data is loaded.
- [ ] AC8: `make panel` reads the encrypted file in process and fails closed (non-zero, no
  file written) when it cannot be decrypted; `--private-file` renders the same panel from a
  plain YAML such as the fake-number fixture.
- [ ] AC9: The new commands, schema and owner steps are in the runbooks.

## References

- Bitácora: #16; `docs/adr/adr-002-*` (isolation), `docs/runbooks/seller-playbook.md`,
  `docs/runbooks/ops.md`, `src/leaving_denver/private_data.py`.
