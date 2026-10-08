# Denver Tech Center Moving Sale — Seller Playbook

Operational guidelines for the sale: household items go by 2026-10-23 and the car by 2026-11-09. Public
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
| **Cars.com (the car only)** | The car's own listing, with the vehicle form | Follow the platform's rules; the listing never carries the phone number | Payment is a cashier's check at the buyer's bank, never a deposit ([vehicle-sale.md](vehicle-sale.md)); take it down when the car is handed over |
| **Complex Portal (ActiveBuilding)** | High-trust local buyers | **Include full catalog link** | State the one-flight walk-up and no-elevator pickup facts before scheduling |

### Listing copy: `/seller/`

Write each listing at `/seller/` (behind Cloudflare Access, same page on a phone and on a
computer; setup in [ops.md](ops.md)). Pick the item and the platform and copy the title,
description, tags and price. It covers:

- **Facebook Marketplace, Craigslist, OfferUp and Nextdoor in English, and Facebook and
  Craigslist in Spanish.** Spanish copy comes from each item's `es` overlay in
  `data/inventory.yaml`.
- **The car.** Mileage, title status and VIN, and a payment line that is only the car's bank
  payment from the data (a cashier's check issued at the buyer's bank, nothing else). It
  never offers cash, Venmo, Zelle or a wire; see [vehicle-sale.md](vehicle-sale.md).
- **Flaws** from the item's `flaws:`, listed after the good points.
- **Limits.** The page shows the counts: Facebook title 100 and description 5000, Craigslist
  title 70, OfferUp title 60. A red count means the text is too long for that platform.
- **No phone number.** Facebook and OfferUp take messages in the app and Craigslist replies
  go through its email relay. The number stays out of every listing. The number a buyer
  texts is the owner's work phone, so nothing is released at the end (#29 was closed as not
  planned).
- **The link.** The per-channel link (its `utm_source` says where the buyer came from) is for
  **chat replies only**. Never paste it into a listing body; the per-item copy has none. The
  full catalog link goes only in an umbrella post, as the table above says.
- **The listing-creator link** per platform (the vehicle form for the car).

Edit the item in `data/inventory.yaml` (or its `es:` overlay), publish as described in
[ops.md](ops.md), and the copy follows; nothing is typed into the tool.

Check each group's rules before posting an umbrella sale message. For
Facebook/Nextdoor, use one local sale post rather than repeating identical
item listings. Use factual titles (brand, model, size and condition), real
photos including any flaws, and first-person, neighborly copy. Do not claim
unverified vehicle service, condition or retail value.

---

## 2. Campaign calendar and price changes

| When | Seller action |
| :--- | :--- |
| September 29–October 4 | Photograph and list the car and highest-value items first; list smaller items after the main listings. Post an umbrella message only where group rules allow it and put a QR flyer on the building board if permitted (print `https://leaving-denver.pages.dev/flyer/` from a browser). |
| October 5–11 | Reply promptly, follow up on qualified inquiries and renew listings only when the platform offers it. Asking prices hold this week (owner, 2026-10-06; #211). |
| October 12–15 | The price drop opens October 13 (the only one before the floors); review items with no messages before changing their public asking prices. If the sectional is unsold, contact The Good Couch with real photos by October 12 as a backup, and book donation/pickup alternatives by October 15 ([backup-exits.md](backup-exits.md)); confirm acceptance first, especially for bedding, electronics and sleeper sofas. |
| October 16–19 | Reserve floors open October 16 for household items. Promote remaining bundles without claiming items already sold. |
| October 20–22 | Household giveaway window: give away or donate what is left; last drop-offs and recycling by October 21 ([backup-exits.md](backup-exits.md)). Take down sold listings. |
| October 23 | Household deadline: take the unsold household items off the catalog ([household close-out](decommission.md)). From here the page is about the car. |
| October 24–November 9 | Sell the car and arrange its handover in this window, never later than November 9 (see [vehicle-sale.md](vehicle-sale.md)); refresh the car's instant offers after October 30 and do not promise a later bank transaction. |
| By November 9 | Car handed over: turn the sale off, take down the car's listings and follow the [decommission runbook](decommission.md) to remove public contact details. Verify the catalog no longer exposes a contact number. |

Run `leaving-denver drops` immediately before repricing. It reads the household windows from `seller.price_schedule` (the car has no schedule) and displays all price tiers:

* **First drop:** reduce items with no qualified inquiries.
* **Clear reserve floors:** use the encrypted per-item minimums.
* **Giveaway window:** dispose of remaining low-value household items before October 23.

The command output is seller-only. Do not publish its dates, reserve timing, or
totals; the displayed tiers come from the inventory and encrypted reserve data
and reveal negotiation strategy. The owner sets asking prices; research
estimates are not instructions to overwrite them. After editing public prices
or marking an item sold, follow [site operations](ops.md) to publish.

### The private views

Open `/seller/` on the phone and type the five-word passphrase under "Private data" (or let
Bitwarden fill it: the passphrase lives in the `leaving-denver-seller` item). The
page decrypts the sealed envelope in the browser (nothing leaves the phone) and shows one row
per item: asking price, target, floor, status, days listed, channels posted, Facebook renew due,
next drop date and the price to drop to, and the price log or sale. A yellow "Due now" box lists
the renewals and the drops whose window has opened. Choosing an item also shows its floor, target
and note. Lock clears it all, and leaving the page does too. A wrong passphrase shows one
message and nothing else.

The phone shows the data as of the last `make ci-secrets` and deploy. A recording made with the
commands below reaches it only after the update they offer (answer yes) or a later
`make ci-secrets` and deploy. See the sealed private data section in [site operations](ops.md).
To skip typing the passphrase when the update asks for it, run the command under dotf:
`dotf secrets run --only SELLER_PASSPHRASE -- make sold ID=sofa-sleeper PRICE=180`.

Record what happens as it happens; each command writes to `data/private.sops.yaml` through
`sops set` (nothing is decrypted to disk). Commit the encrypted file afterwards.

| When | Command |
| :--- | :--- |
| You post an item, or renew it | `make post ID=sofa-sleeper CHANNEL=facebook` (channels: facebook, craigslist, offerup, nextdoor, activebuilding, and carscom for the car only; add `ON=2026-10-01` for a post made earlier) |
| You change an asking price | `make reprice ID=sofa-sleeper PRICE=195` sets `recommended_list_price` in `data/inventory.yaml` (that one line, comments kept) and records it in the private price log; then publish as in [site operations](ops.md). A date after today is refused (#236) |
| An item sells | `make sold ID=sofa-sleeper PRICE=180` records price and date and lists the channels to take it down from |

**Social posts.** Open `https://leaving-denver.pages.dev/social/` on the phone. Press and hold
each image to save it (`post.jpg` for the feed, `story.png` for a story), copy the caption, and
use the link for that network: Instagram's bio or link sticker, Facebook, WhatsApp. Each link
counts as its own channel in the dashboard. The images are rebuilt on every deploy, so sold items
drop out of the collage; save them again after a sale before the next post.

The next drop is the first window the price log does not cover yet (first drop, then clear
floors). The first steps halfway to the floor from the asking price in force, to the nearest $5
($100 for the car); the second is the floor. The second drop window was removed when the first
moved to October 13 (#211). Afterwards, compare each item's price log
with its sale in the private views to see whether a drop moved it.

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
only after confirming a time; disclose second-floor pickup, one flight of
stairs and no elevator before scheduling. Meet in daylight when possible,
stage small items at the door, have another adult present for furniture, and
do not let a stranger enter while you are alone. Meet car buyers away from
the apartment, following the vehicle runbook.

---

## 4. The Car

The car has its own runbook: [vehicle-sale.md](vehicle-sale.md) covers screening, the test drive, the delayed-handover agreement, payment at the bank, the Colorado paperwork and the plates.
