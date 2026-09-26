---
id: "lesson-dealer-recall-closure-prior-to-listing"
type: lesson
scope: local
tags: [movingsale, vehicle, sales, legal, recalls]
created: "2026-09-25"
source: "Denver moving sale platform development"
---

# Lesson: Closing Manufacturer Recalls at Dealer Prior to Listing Neutralizes Buyer Renegotiation

## Context (The Problem/Error)
> "Used car flippers and prospective private buyers routinely run the vehicle VIN on NHTSA and Carfax, using open recall notices as leverage to demand $1,000–$2,000 discounts or abandon negotiations."

Listing a vehicle with an open recall campaign introduces immediate liability questions regarding vehicle roadworthiness and road safety.

## The Finding (Root Cause/Solution)
The root cause was listing the vehicle before verifying and closing open manufacturer campaigns.
The correct solution was taking the vehicle to an authorized Ford dealership to complete and officially close the recall campaign the week prior to listing. Explicitly documenting "Zero Open Recalls (Official Ford dealership campaign completion invoice provided)" converts an objection into a premium selling feature.

## Anti-Pattern (What NOT to do)
Do not list a private party vehicle with unresolved or unverified manufacturer safety recalls.

## Golden Rule (The Pattern)
> **Whenever preparing a vehicle for private liquidation, verify NHTSA recall status and have the franchised dealer officially close all open campaigns before publishing the VIN.**

## References
- `data/inventory.yaml` (`car_ford_escape.condition.open_recalls: 0`)
- `research/market_and_platform_guide.md` (Colorado private car sales protocol)

## Correction (2026-09-25)
Closing recalls is only half of the paperwork story. Two claims next to it in the listing were
wrong and have been fixed:
- **Emissions:** Colorado requires the seller to hand over a passing test that was *not already
  used* to register or renew the car. A test consumed by the seller's own renewal does not count,
  even if it has not expired. The listing now promises a new certificate at sale.
- **Coverage:** Ford's 1.5L coolant-intrusion program (CSP 21N12) ends at 84k miles; this car is at
  103.5k. "Zero open recalls" must never be read as "the engine program was done". Prove completed
  work with the dealer's service-history (OASIS) printout, and welcome a pre-purchase inspection.
