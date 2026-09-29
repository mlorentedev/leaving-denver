---
id: "lesson-stock-photo-hazard-used-car-listings"
type: lesson
scope: local
tags: [movingsale, fraud, marketplace, vehicle, photography]
created: "2026-09-25"
source: "Denver moving sale platform development"
---

# Lesson: Stock Photos on High-Value Vehicles Trigger Fraud Signals in Private Party Sales

## Context (The Problem/Error)
> "The vehicle (2019 Ford Escape SEL AWD) represents nearly all of the liquidation value, but initial posting drafts used manufacturer stock photos."

In private US classifieds (Facebook Marketplace, Craigslist, OfferUp), listings of vehicles that use marketing renders or dealer stock photography are universally treated by prospective buyers as out-of-town wire transfer scams, resulting in automated user reports and platform shadowbans.

## The Finding (Root Cause/Solution)
The root cause was prioritizing cosmetic image perfection over buyer trust and physical asset verification.
The correct solution is enforcing an authentic photo package: real-world photography showing the vehicle parked in DTC, the physical odometer showing 103,500 miles, engine bay, tire tread depth, interior upholstery, and the seller holding the physical Colorado title in hand.

## Anti-Pattern (What NOT to do)
Do not use press renders, manufacturer stock photos, or cropped dealer catalog images when liquidating motor vehicles in peer-to-peer marketplaces.

## Golden Rule (The Pattern)
> **Whenever listing high-value vehicles in private classifieds, only use authentic, timestamped in-situ photos including the odometer and clean physical title in hand.**

## References
- Vault: `10_projects/leaving-denver/research/photo-forensic-audit.md` (inspection of visual trust signals)
- `data/inventory.yaml` (Asset specification and photographic requirements)
