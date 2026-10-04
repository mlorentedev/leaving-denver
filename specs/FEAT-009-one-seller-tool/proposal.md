---
id: "FEAT-009-one-seller-tool"
type: spec
status: implementing # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#140"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# FEAT-009: One seller tool, the same on a phone and on a computer

## Why

<!-- from issue #140: FEAT-009: one seller tool -->

The owner has two seller tools. `/seller/` (public build, behind Cloudflare Access) is
phone-friendly but thin: English only, one flat template, no car copy, no scam replies. The
local `templates/poster_assistant.html` (833 lines, never deployed) writes better copy, in
Spanish too, and knows the car, but it needs the owner's computer, a JavaScript PIN and the
private floors. The owner wants one tool, at `/seller/`, usable the same way anywhere, so the
copy has to be at least as good there as in the local assistant, with nothing private in it.

Access is configured and verified, but the rule stays: the public build never holds floors,
reserve or target prices, notes or a PIN, even behind Access (`docs/runbooks/ops.md`). So this
change moves the public-safe half of the assistant first. The private half is PR 2.

## What (PR 1: the public-safe copy)

`/seller/` gets everything of the assistant's copy generation that needs no private data:

- **Spanish.** Two more channels, Facebook (Español) and Craigslist (Español), written from
  the item's `es` overlay, the page's own language labels and the Spanish payment labels.
- **The car.** Vehicle copy for every channel: mileage, title status and VIN, no
  dimensions, a test-drive closing, and the car's payment from the data.
- **Payment wording is data.** Each item ships its payment terms, built from
  `seller.payment_methods` and the locales: the household methods "in person", and the car's
  cashier's check or wire transfer only. Neither `seller.mjs` nor `seller.html` spells out a
  payment method.
- **Flaws** from `flaws:` (and `es.flaws`), after every positive.
- **Voice and content.** First person singular, plain facts only, "No holds and no
  deposits", a bundle line for household items. No phone number anywhere, no retail anchor,
  no tax math, no invented selling points.
- **Limits.** Facebook title 100 and description 5000, Craigslist title 70, OfferUp title 60.
  The page shows the counts; an overlong title is flagged, never silently cut.
- **Links.** Per-channel `utm_source`, the Spanish channels linking `/es/i/<id>/`. The link is
  a separate field for chat replies and is never inside a listing body.
- **Scam replies.** Six replies (verification code, fake payment email, overpayment,
  courier, vehicle-report link, deposit), each in English and Spanish with its own copy
  button, from `data/seller-replies.yaml`. The car's payment methods are filled in from the
  data.
- **The assistant's other helpers**: the listing-creator link per platform (the vehicle
  form for the car), search tags, copy price, copy title + price + description, and the
  photos in upload order.

Where it lives: `assets/seller.mjs` (copy), `templates/seller.html` (page),
`site_builder.py` (`seller_items`, `seller_replies`, `write_seller_poster`: the payload),
`data/seller-replies.yaml` (the replies).

## Out of scope

- Removing `poster_assistant.html`. It stays, unchanged, until PR 2.
- **Left in `poster_assistant.html` for PR 2** (they need private data or a decision):
  - the three-week plan and the per-item floors (`firm_floor_price`, `recommended_list_price`
    by week), the week-by-week price in the dropdown and the negotiation script;
  - `[DRAFT]` items (unpublished) in the selector;
  - the seller's phone in the Craigslist and Nextdoor copy (#29 plans a Google Voice number;
    PR 1's copy offers the platform chat and Craigslist's relay instead);
  - the "Orig: $" retail anchor in the header.
- **Dropped, not moved** (wrong or unsafe, not just private): the JavaScript PIN (`8011`),
  the x1.15 tax math, the retail "bought new for" lines, the hard-coded cash/Venmo/Zelle
  wording, and selling points no data backs ("100% assembled", "no hidden defects",
  "non-smoking, pet-free apartment" on every item).
- Spanish for OfferUp and Nextdoor (the assistant has none either).
- Gutters: `<main>` padding (PR #141) is not touched.

## PR 2 (decided by ADR-007, which amends ADR-002, ADR-005, ADR-006 and the runbook rule on floors)

Out of scope here: the private data (floors, notes, tracking) reaches
`/seller/` only as **passphrase-encrypted ciphertext**, decrypted in the browser, so that
turning off the edge policy still discloses nothing. PR 2 would:

1. follow ADR-007 (`docs/adr/adr-007-private-seller-data-travels-as-ciphertext.md`); its
   acceptance criteria are in `pr2-encrypted-private-data.md`;
2. add the ciphertext to the build from `data/private.sops.yaml` without ever printing it;
3. move the plan, floors, negotiation and tracking into `/seller/` behind the passphrase;
4. delete `poster_assistant.html`, `build/private/` and the PIN, and update
   `verify_security_guarantees` and the isolation tests to match.

PR 1 adds no ciphertext, no passphrase and no private field to `/seller/`.

## Risks / open questions

- The car's pickup note already states its payment, so the car's listing says it twice
  (the pickup line, then `Payment:`). Kept: the `Payment:` line is the data-driven, tested
  statement; the pickup note is the owner's free text.
- The scam replies in `docs/runbooks/seller-playbook.md` section 3 were the source of the
  text. The playbook now points to `/seller/` and `data/seller-replies.yaml` rather than
  keeping a second copy.
- A new platform needs an entry in `CHANNELS` (limits, creator link) and an intro and a
  closing; the tests iterate `CHANNELS`' six names, so a new one needs adding there too.

## Acceptance criteria

- [ ] AC1: The Spanish channels (`fb-es`, `cl-es`) write the listing from each item's `es`
  overlay (title, condition, specs, pickup) and the Spanish labels; the English channels
  show none of it. The overlay is complete for every listable item.
- [ ] AC2: The car's copy on every channel is vehicle copy (mileage, title status, VIN, no
  dimensions, no bundle line) and its payment is the car's methods from the data, in
  the page's language, with no cash, Venmo or Zelle.
- [ ] AC3: Every item's payment wording comes from `seller.payment_methods` and the locales;
  `seller.mjs` and `seller.html` contain none of it.
- [ ] AC4: `Known flaws:` / `Defectos conocidos:` comes after every positive line, follows the
  language, and is absent when the item has none.
- [ ] AC5: Every listing on every channel is first person singular (English and Spanish),
  says "No holds and no deposits", carries no phone number, no hype, no retail or tax math,
  and no dollar amount other than the asking price.
- [ ] AC6: Every real item fits every channel's title limit uncut and Facebook's 5000
  description limit; an overlong title is flagged in `fits`, an overlong description is
  never cut.
- [ ] AC7: Each channel's link has its own `utm_source` and the page's origin, the Spanish
  channels link `/es/i/<id>/`, and no listing body contains a link.
- [ ] AC8: The page has six scam replies, each in English and Spanish in a read-only
  textarea with a copy button, from `data/seller-replies.yaml`; the car's payment is filled
  from the data; the build fails on a reply without both languages or with an unknown
  placeholder; the replies are first person singular and phone-free.
- [ ] AC9: `/seller/index.html` and `seller.mjs` contain no floor, reserve or target price,
  internal note, PIN, session storage or phone number; the page template receives only
  `items_json`, `config_json` and `replies`.
- [ ] AC10: In a browser, the platform and item controls rewrite the listing, the counters
  and creator link follow the channel, and every copy button (title, description, tags,
  link, price, title + price + description, each reply) puts what is on screen on the
  clipboard.
- [ ] AC11: `poster_assistant.html` is unchanged and still absent from `build/public/`.

## References

- Bitácora: #140 (this), #29 (Google Voice number), #141 (gutters).
- `docs/runbooks/seller-playbook.md` (sections 1 and 3), `docs/runbooks/ops.md` (Access),
  `docs/runbooks/vehicle-sale.md` (payment).
- `tests/test_inventory_ssot.py::test_the_car_takes_only_payments_that_cannot_be_clawed_back`
