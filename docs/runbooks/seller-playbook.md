# Denver Tech Center Moving Sale — Seller Playbook

Operational guidelines for the sale before the 2026-11-09 departure. Public
prices come from `data/inventory.yaml`; reserve floors live encrypted in
`data/private.sops.yaml`. Dates below are planning checkpoints, not promises
to buyers. Confirm current listings and platform rules before posting.

---

## 1. Multi-Platform Channel Strategy

| Platform | Role in Funnel | Linking Rule | Key Negotiation Rule |
| :--- | :--- | :--- | :--- |
| **Facebook Marketplace** | Local buyer inquiries | Share catalog link in chat after interest; avoid duplicate listings | Check whether Renew is available after 7 days; do not delete/relist daily |
| **Craigslist Denver** | Cash-ready buyers & tech items | **Include full catalog link** in master ad | Free posts may be renewed after 48 hours; paid cars/trucks-by-owner posts ($5) cannot be renewed: repost only after expiry |
| **OfferUp** | Mobile impulse same-day pickups | **NO external links** | Require same-day pickup for discounts |
| **Nextdoor (DTC)** | Neighborhood buyers | **Include full catalog link** | No duplicate listings or delete/repost to bump; use For Sale & Free for items |
| **Complex Portal (ActiveBuilding)** | High-trust local buyers | **Include full catalog link** | State the one-flight walk-up and no-elevator pickup facts before scheduling |

### Listing copy: `/seller/`

Write each listing at `/seller/` (behind Cloudflare Access, same page on a phone and on a
computer; setup in [ops.md](ops.md)). Pick the item and the platform and copy the title,
description, tags and price. It covers:

- **Facebook Marketplace, Craigslist, OfferUp and Nextdoor in English, and Facebook and
  Craigslist in Spanish.** Spanish copy comes from each item's `es` overlay in
  `data/inventory.yaml`.
- **The car.** Mileage, title status and VIN, and a payment line that is only the car's bank
  payments from the data (cashier's check issued at the buyer's bank, or wire transfer). It
  never offers cash, Venmo or Zelle; see [vehicle-sale.md](vehicle-sale.md).
- **Flaws** from the item's `flaws:`, listed after the good points.
- **Limits.** The page shows the counts: Facebook title 100 and description 5000, Craigslist
  title 70, OfferUp title 60. A red count means the text is too long for that platform.
- **No phone number.** Facebook and OfferUp take messages in the app and Craigslist replies
  go through its email relay. The number stays out of every listing (#29 plans a Google Voice
  number).
- **The link.** The per-channel link (its `utm_source` says where the buyer came from) is for
  **chat replies only**. Never paste it into a listing body; the per-item copy has none. The
  full catalog link goes only in an umbrella post, as the table above says.
- **The listing-creator link** per platform (the vehicle form for the car).

Edit the item in `data/inventory.yaml` (or its `es:` overlay), publish as described in
[ops.md](ops.md), and the copy follows; nothing is typed into the tool. Floors and
negotiation are not in `/seller/`: they stay in the local assistant until FEAT-009 PR 2.

Check each group's rules before posting an umbrella sale message. For
Facebook/Nextdoor, use one local sale post rather than repeating identical
item listings. Use factual titles (brand, model, size and condition), real
photos including any flaws, and first-person, neighborly copy. Do not claim
unverified vehicle service, condition or retail value.

---

## 2. Campaign calendar and price changes

| When | Seller action |
| :--- | :--- |
| September 29–October 4 | Photograph and list the car and highest-value items first; list smaller items after the main listings. Post an umbrella message only where group rules allow it and put a QR flyer on the building board if permitted. |
| October 5–11 | Reply promptly, follow up on qualified inquiries and renew listings only when the platform offers it. Review items with no messages before changing their public asking prices. |
| October 12–18 | Refresh eligible listings and photos; follow up with interested buyers. Recheck public asking prices on items still getting no qualified inquiries. |
| October 19–25 | Promote remaining bundles without claiming items already sold. If the sectional is unsold, contact The Good Couch with real photos by October 22 as a backup; see [backup-exits.md](backup-exits.md). |
| October 26–November 1 | Reassess unsold items and book donation/pickup alternatives by October 26 ([backup-exits.md](backup-exits.md)); confirm acceptance first, especially for bedding, electronics and sleeper sofas. Refresh car instant offers around November 1–2; see [vehicle-sale.md](vehicle-sale.md). |
| November 2–8 | Give away or donate remaining low-value items if needed. Arrange vehicle handover for November 5, with November 6 as the latest fallback; do not promise a later bank transaction. Take down sold listings and follow the [decommission ticket](https://github.com/mlorentedev/leaving-denver/issues/38) to remove public contact details. |
| November 9 | Departure: verify the sale has ended and the catalog no longer exposes a contact number. |

Run `leaving-denver drops` immediately before repricing. It derives schedule windows from `seller.departure_date` and displays all price tiers:

* **First drop:** reduce items with no qualified inquiries.
* **Second drop:** make the next controlled reduction.
* **Clear reserve floors:** use the encrypted per-item minimums.
* **Giveaway window:** dispose of remaining low-value items before departure.

The command output is seller-only. Do not publish its dates, reserve timing, or
totals; the displayed tiers come from the inventory and encrypted reserve data
and reveal negotiation strategy. The owner sets asking prices; research
estimates are not instructions to overwrite them. After editing public prices
or marking an item sold, follow [site operations](ops.md) to publish.

### The control panel

`make panel` writes `build/private/panel.html` (open it in a browser, or `make serve` and visit
`/private/panel.html` on loopback). One row per item: asking price, target, floor, status, days
listed, channels posted, Facebook renew due, next drop date and the price to drop to, and the
price log or sale. A yellow "Due now" box lists the renewals and the drops whose window has
opened. It decrypts the private file in process and writes nothing else; it needs the age key
and fails without writing if it cannot decrypt. It is never deployed (ADR-006).

Record what happens as it happens; each command writes to `data/private.sops.yaml` through
`sops set` (nothing is decrypted to disk). Commit the encrypted file afterwards.

| When | Command |
| :--- | :--- |
| You post an item, or renew it | `make post ID=sofa-sleeper CHANNEL=facebook` (channels: facebook, craigslist, offerup, nextdoor, activebuilding; add `ON=2026-10-01` for a post made earlier) |
| You change an asking price | edit `recommended_list_price` in `data/inventory.yaml`, then `make reprice ID=sofa-sleeper PRICE=195` (the panel flags a log that differs from the asking price) |
| An item sells | `make sold ID=sofa-sleeper PRICE=180` records price and date and lists the channels to take it down from |

The next drop is the first window the price log does not cover yet (first drop, second drop,
clear floors). The first two step halfway to the floor from the asking price in force, to the
nearest $5 ($100 for the car); the last is the floor. Afterwards, compare each item's price log
with its sale in the panel to see whether a drop moved it.

Targets are recorded for each household item except the topper (2026-10-01, #32). They are the expected-close prices from the 2026-09-25 pricing research. Research says the topper goes with the sofa, not alone, so it has none. Change any of them with `make secrets` (it opens the editor):

```yaml
targets:
  sofa-sleeper: 190   # researched expected close, USD, per item id
```

---

## 3. Objection Handling & Fast Response Scripts

### "Is this still available?"
> "Yes, it is available. Can you pick up in DTC (80111) today or tomorrow?
> What time works?"

### A low offer
> "Thanks for the offer. That is below today's asking price. I can do
> $[amount you actually approve] for pickup [day]. Does that work?"

### A hold request
> "I cannot hold it without a confirmed pickup. If it is still available on
> [day], message me and we can arrange a time. No deposit needed."

### Confirming a showing / no-show
> "Still on for [time] today? Please reply YES before I share the meeting
> details." If there is no confirmation, do not travel or hold the item;
> offer the backup buyer a time. After a no-show: "I missed you at [time].
> Let me know if you can confirm a new pickup slot; it remains available."

### Scam replies

`/seller/` has six replies, each in English and Spanish with its own copy button: a code
sent to your phone (Google Voice or another), a payment email or screenshot, overpayment,
couriers and shipping, a vehicle-report link, and deposits or holds. Their text lives in
`data/seller-replies.yaml` (edit it there, not here); the car's payment methods in them come
from the inventory. The rule behind all six: payment counts only when it shows in your own
app, or at the bank for the car, and only for the exact price at local pickup.

For household items, count cash when you receive it. Count in-person
Venmo/Zelle only after the payment appears in **your own** app. Do not request
deposits. Give the precise address
only after confirming a time; disclose first-floor pickup, one flight of
stairs and no elevator before scheduling. Meet in daylight when possible,
stage small items at the door, have another adult present for furniture, and
do not let a stranger enter while you are alone. Meet car buyers away from
the apartment, following the vehicle runbook.

---

## 4. The Car

The car has its own runbook: [vehicle-sale.md](vehicle-sale.md) covers screening, the test drive, the delayed-handover agreement, payment at the bank, the Colorado paperwork and the plates.
