---
id: "lesson-in-modal-contextual-upselling-conversion"
type: lesson
scope: local
tags: [movingsale, conversion, merchandising, bundles, ui]
created: "2026-09-25"
source: "Denver moving sale platform development"
---

# Lesson: Contextual In-Modal Upsells Outperform Static Footer Bundle Cards

## Context (The Problem/Error)
> "Displaying 7 large package bundle cards in a permanent section at the bottom of the catalog page created visual noise, mobile scroll fatigue, and distracted buyers from individual item details."

Classified buyers arrive with specific search intent (e.g. looking only for an office desk, a sleeper sofa, or kitchen appliances) and ignore disconnected bulk bundles.

## The Finding (Root Cause/Solution)
The root cause was decoupling package deals from the individual high-intent purchase decision.
The correct solution is contextual upselling inside the item detail sheet, backed by a separate bundle sheet that lists every included item. When a buyer views the Sleeper Sofa, the item sheet highlights the sofa-and-topper bundle for $220 ($35 savings). When viewing the desk, it presents the home-office bundle for $150 ($30 savings). This presents the offer at the exact moment of peak interest without bloating the primary grid.

## Anti-Pattern (What NOT to do)
Do not clutter catalog footers with generic package cards that compete with single-item discovery.

## Golden Rule (The Pattern)
> **Whenever merchandising product bundles, present them as contextual upsells within the specific item detail views of their constituent parts.**

## References
- [Vault research: bundle strategy](https://github.com/mlorentedev/knowledge/blob/main/10_projects/leaving-denver/research/bundle-strategy.md)
- `src/leaving_denver/site_builder.py` (`sanitize_public_inventory` bundle calculations)
- `src/leaving_denver/templates/index.html` (item and bundle sheets)
