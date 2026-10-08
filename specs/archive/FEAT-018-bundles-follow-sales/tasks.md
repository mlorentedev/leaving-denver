---
tags: [spec, tasks]
created: "2026-10-06"
---

# Tasks - FEAT-018-bundles-follow-sales

## Setup

- [x] Branch `feat/bundles-follow-sales`, stacked on #206 (both edit `data/inventory.yaml` and the same tests)
- [x] `proposal.md` complete; owner decisions recorded (20%, round down to $5, replace Living room media)

## Implementation

- [x] [AC1][AC2][AC3] `tests/test_everything_bundle.py` written first; 11 of 12 failed before the builder change
- [x] [AC1][AC2][AC3] `everything_offer` and `everything_price` in `site_builder.py`; `sanitize_public_inventory` derives the everything bundle
- [x] [AC4][AC5] `data/inventory.yaml`: Take everything keeps `discount_pct: 20` only; `bundle-living-room` replaced by `bundle-sofa-tv-table`
- [x] Tests that read a typed everything list compute the derived one (`offered()` in `test_build_contract.py`, `test_inventory_ssot.py`, three `b.get("items", [])`)

## Verification

- [x] Full suite green; rendered page checked
