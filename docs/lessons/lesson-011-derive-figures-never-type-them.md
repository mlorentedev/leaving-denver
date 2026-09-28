---
id: "lesson-derive-figures-never-type-them"
type: lesson
scope: local
tags: [data, templates, testing]
created: "2026-09-27"
source: "BUG-001 PR 3: bundle savings drifted from item prices (#6)"
---

# Lesson: Derive Figures at Build Time, Never Type Them

## Context (The Problem/Error)
Each bundle carried `individual_total` and `savings` typed into the YAML, and the page carried
a hand-typed "$540 (Save $173)" banner plus a JS `UPSELL_MAP` with its own prices. When item
prices moved, three copies of the same arithmetic disagreed, and nothing failed.

## The Finding (Root Cause/Solution)
A number that is a function of other data is a cache, and a hand-maintained cache drifts.
The builder now computes totals and savings from the public item prices (a free item counts
as $0), and the page renders them server-side from that one result.

## The Guard
- `test_bundles_integrity` forbids `individual_total` and `savings` keys in the YAML.
- `test_page_figures_match_the_data` recomputes every figure from the YAML independently of the
  builder and checks the rendered cards, and fails on any "Save $N" the data does not produce.

## Also
Jinja2 resolves `b.items` on a dict to the `dict.items` method; use `b['items']`.
