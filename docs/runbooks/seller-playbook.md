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

Check each group's rules before posting an umbrella sale message. For
Facebook/Nextdoor, use one local sale post rather than repeating identical
item listings. Use factual titles (brand, model, size and condition), real
photos including any flaws, and first-person, neighborly copy. Do not claim
unverified vehicle service, condition or retail value.

---

## 2. Campaign calendar and price changes

| When | Seller action |
| :--- | :--- |
| Now–early October | Photograph and list the car and highest-value items first; list smaller items after the main listings. Post an umbrella message only where group rules allow it and put a QR flyer on the building board if permitted. |
| Weekly through October | Reply promptly, check unanswered inquiries and renew only when the platform offers it. Review items with no qualified messages before changing their **public** prices. Never publish private floors or claim a price increase. |
| By October 22 | If the sectional is unsold, contact The Good Couch with real photos as a backup; see [OPS-010](https://github.com/mlorentedev/leaving-denver/issues/35). |
| Late October–November 1 | Reassess remaining items and arrange donation/pickup alternatives early; do not assume any charity accepts bedding, electronics or sleeper sofas. Refresh car instant offers around November 1–2; see [vehicle-sale.md](vehicle-sale.md). |
| November 3–6 | Give away or donate remaining low-value items if needed; arrange vehicle handover by November 5, with November 6 as the latest fallback. Do not promise a later bank transaction. |
| Before November 9 | Remove sold listings and close the sale; follow the [decommission ticket](https://github.com/mlorentedev/leaving-denver/issues/38) to remove public contact details. |

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

### Scam scripts

- **Verification code:** "I do not share login or verification codes. We
  can meet in person."
- **Fake payment or 'business account upgrade':** "I only accept payment
  that shows in my own app while you are here. I do not act on emails or
  screenshots, and I will not pay a fee to receive money."
- **Overpayment, courier or shipping:** "Exact amount at local pickup only;
  no couriers, shipping, extra checks or refunds." For the car, use only the
  bank payment methods in [vehicle-sale.md](vehicle-sale.md).
- **Vehicle-report link:** "You can run a report through a service you
  choose; I do not buy reports from links sent by buyers."

For household items, cash or in-person Venmo/Zelle counts only once receipt
shows in **your own** app. Do not request deposits. Give the precise address
only after confirming a time; disclose first-floor pickup, one flight of
stairs and no elevator before scheduling. Meet in daylight when possible,
stage small items at the door, have another adult present for furniture, and
do not let a stranger enter while you are alone. Meet car buyers away from
the apartment, following the vehicle runbook.

---

## 4. The Car

The car has its own runbook: [vehicle-sale.md](vehicle-sale.md) covers screening, the test drive, the delayed-handover agreement, payment at the bank, the Colorado paperwork and the plates.
