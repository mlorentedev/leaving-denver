# Denver Tech Center Moving Sale — Seller Playbook

Operational guidelines for maximizing return before the 2026-11-09 departure. Public prices come from `data/inventory.yaml`; reserve floors live encrypted in `data/private.sops.yaml`.

---

## 1. Multi-Platform Channel Strategy

| Platform | Role in Funnel | Linking Rule | Key Negotiation Rule |
| :--- | :--- | :--- | :--- |
| **Facebook Marketplace** | Primary traffic driver (65% volume) | **NO links in ad description** (send link in 1st chat response) | List 10-15% above floor to allow counter-offer |
| **Craigslist Denver** | Cash-ready buyers & tech items | **Include full catalog link** in master ad | Renew/bump every 48 hours sharp |
| **OfferUp** | Mobile impulse same-day pickups | **NO external links** | Require same-day pickup for discounts |
| **Nextdoor (DTC)** | High-trust affluent neighbors | **Include full catalog link** | Emphasize neighborly relocation story |
| **Complex Portal (ActiveBuilding)** | High-trust local buyers | **Include full catalog link** | State the one-flight walk-up and no-elevator pickup facts before scheduling |

---

## 2. Departure-Date Pricing Schedule

Run `leaving-denver drops` to derive the current windows and price tiers from `seller.departure_date`:

* **First drop:** October 3–6.
* **Second drop:** October 15–17.
* **Clear reserve floors:** October 20–25.
* **Giveaway window:** November 3–5, before the November 9 departure.

Do not copy a total into this runbook. The command calculates current prices from the inventory and encrypted reserve data.

---

## 3. Objection Handling & Fast Response Scripts

### The "Is this still available?" Filter:
> *"Hi! Yes, it's available, assembled, and ready for pickup in the Denver Tech Center. We're moving abroad in November, so it's first come, first served. When would you like to come test it out?"*

### The Aggressive Lowballer:
> *"Thanks for the offer, but that is below today's price. The lowest I can do for pickup today is $[current tier]. If you can pick it up today or tomorrow, it's yours."*

### The "Hold It Until Next Week" Request:
> *"Since we are leaving the country on a firm deadline, I cannot hold items on verbal promises. If you want to come by sooner you're welcome to, or if it's still here on Saturday morning send me a message and we'll arrange the pickup."*

### The Advance Zelle/Courier Scam:
> *"I only accept cash or in-person Venmo/Zelle when the buyer is physically present in DTC to inspect the item. No advance wire transfers or third-party couriers."*

A Venmo or Zelle payment counts only once it shows in **your own** app. A screenshot or an email "from Zelle" is not a payment. Stage items near the apartment door, disclose the one flight of stairs before scheduling, and never have a buyer in the apartment while you are alone.

---

## 4. The Car

The car has its own runbook: [vehicle-sale.md](vehicle-sale.md) covers screening, the test drive, the delayed-handover agreement, payment at the bank, the Colorado paperwork and the plates.
