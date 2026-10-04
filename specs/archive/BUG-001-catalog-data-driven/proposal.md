---
id: "BUG-001-catalog-data-driven"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-26"
issue: "mlorentedev/leaving-denver#6"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# BUG-001: Catalog rendered from data

## Why

<!-- from issue #6: BUG-001: Catalog renders broken bundles and hardcoded figures -->

Most of what a buyer reads on the catalog is written by hand in `templates/index.html`, not taken from `data/inventory.yaml`, and it has already drifted:

- The bundle cards read fields the data does not have and render `Save $undefined`.
- The hero says "3 weeks" against a 9 November departure.
- The counts and the whole-apartment total are stale constants.
- The vehicle card claims things the YAML does not back.

Listing starts in early October. A buyer who spots one wrong fact stops trusting the rest, and every price or item change today has to be repeated by hand in the template. The build also fails open: if the inventory injection regex stops matching, the page ships the placeholder data with no error.

## What

The builder renders the public page from the YAML with Jinja2 (ADR-003). After this spec:

1. The build fails closed. A missing inventory marker, a field a template uses but the data lacks, or a category with no filter chip stops `make build`.
2. Every figure and claim on the page comes from `inventory.yaml`:
   - bundle names, prices and savings;
   - item counts and the whole-apartment total;
   - the departure date and a countdown;
   - payment terms per item kind;
   - the vehicle card's specs.
3. An item with `published: false` is absent from `build/public/`, with any bundle that contains it, and present under `build/private/` marked DRAFT (FEAT-009).
4. The page does not scroll sideways at 390 px.
5. The page is built for a phone first, with minimal copy. Almost every buyer opens it on a phone. The owner approved the layout on 2026-09-28 (mockup: https://claude.ai/code/artifact/30405956-d62d-4e8a-b7b3-9902e49acfd5, private to the owner). It has:
   - a two-line hero;
   - the car as one wide card;
   - scrollable category chips;
   - a two-column item grid where the whole card opens the item;
   - a scrollable row of bundle cards and one "take everything" card;
   - a two-sentence pickup block;
   - one sticky "Text me" bar as the only contact button;
   - the item detail as a bottom sheet with at most four key facts.

   PRs 3 to 5 build this structure as they move each section to the templates, so no section is rendered from data twice.

The work lands as six PRs, in this order. PR 6 was added on 2026-09-27 at the owner's request; it needs the Jinja2 templates from PR 2. The mobile-first layout was added to PRs 3 to 5 on 2026-09-28. Each stays under ~300 lines of production diff.

| PR | Scope | Closes |
|----|-------|--------|
| 1 | Fail-closed inventory marker; `published` filter for items and bundles, DRAFT in private | #41 |
| 2 | Jinja2 swap with no visible change: `StrictUndefined`, the page rendered from the same data, contract tests | #21 |
| 3 | Filter chips, item grid, bundle row, "take everything" card and `UPSELL_MAP` from data, in the mobile layout; bundle totals and savings computed from item prices; walnut bundle dropped | #6, #32 (bundle part) |
| 4 | `departure_date` replaces `moving_deadline` (countdown, wording, `drops` computed from the date); hero, vehicle card and pickup block from data in the mobile layout, with the minimal copy; payment terms per kind; BUG-007 copy fixes | #13, #9, #48 |
| 5 | Mobile shell: sticky "Text me" bar, item bottom sheet, horizontal-scroll fix at 390 px | #10 |
| 6 | Spanish version: the page rendered per locale to `build/public/` and `build/public/es/`, a language switch, Spanish copy for the item fields, SMS intents in the page's language | #53 |

## Out of scope

Each item below already has its own ticket and comes after this spec. None of them may enter these PRs:

- Tailwind v4 build step (#8): its own spec, once the HTML is stable.
- Accessible dialog, desktop contact and contrast (FEAT-003 #15); statuses (FEAT-006 #18); richer fields (FEAT-007 #19); link previews and per-item pages (FEAT-002 #14); the vehicle "verify it yourself" section (FEAT-008 #37).
- Research price targets in private data (the target half of OPS-007 #32), and the private control panel (FEAT-004 #16).

## Risks / open questions

- **Owner input blocks PR 4, not PRs 1–3.** From BUG-007 #48: is "Everything was bought new" true for every item; is there a receipt for the 100k service; and does the dealer inspection replace "great mechanical shape"? Any claim not confirmed by the time PR 4 is written is dropped.
- **The voice is the owner's call:** resolved: first person singular (#70); the sticky bar says "Text me" (owner, 2026-09-28: direct and personal).
- **The car's publish date is the owner's call.** PR 1 adds the flag. PR 2, once the vehicle card is a template, sets it to `false` for the car until the owner says otherwise, so the preview shows the car only in `build/private/`.
- **The injected sanitized JSON must still hold nothing private.** Moving to Jinja2 must not start passing the full inventory to templates. PR 2 renders from the sanitized dict only, and `verify_security_guarantees` keeps running.
- **`save_inventory_yaml` rewrites the YAML on every build (BUG-006 #12).** New fields added here must survive that round trip. Not fixed here, but PR 1 tests it.

## Acceptance criteria

- [ ] AC1: Removing the inventory marker from the template makes `make build` exit non-zero with a message naming the marker.
- [ ] AC2: A contract test builds with one unpublished item and one bundle containing it. Neither id appears anywhere under `build/public/`; both appear under `build/private/`, the item marked DRAFT.
- [ ] AC3: A template that references a field the data lacks fails the build (`StrictUndefined`), shown by a test that renders a template with a misspelled field.
- [ ] AC4: A test asserts that every number on the rendered page matches the value derived from `inventory.yaml`:
  - every bundle price and savings figure;
  - the item count;
  - the whole-apartment total.
- [ ] AC5: A test asserts that every item category has a filter chip, and the build fails when one does not.
- [ ] AC6: `rg -i "3 weeks|everything must go|highway miles|remote start|Within 2 weeks"` over `src/` and `data/` returns nothing, and a test asserts the vehicle card shows only specs present in the YAML.
- [ ] AC7: Venmo and Zelle appear only next to household items. The vehicle shows cash or a cashier's check, and nothing on the page says "no advance deposits" for the car.
- [ ] AC8: At 390 px the page is 390 px wide (`document.documentElement.scrollWidth`), checked against the preview deploy.
- [ ] AC9: `build/public/es/index.html` exists with `lang="es"`, and every item title, spec and UI string is in Spanish, falling back to English only where the data has no Spanish text. A test lists the fallbacks, and the claim guard runs over the Spanish copy too.
- [ ] AC10: The page follows the approved mobile layout, and a test checks it on the rendered HTML:
  - the header has no contact button, and one sticky "Text me" bar is always on screen;
  - the item grid has two columns below 640 px;
  - the hero is at most 20 words;
  - the item sheet shows at most four facts.

  On the preview at 390 px, every tap target is at least 40 px tall (checked manually, like AC8).

## References

- Issues: #6 (gate), #41, #21, #32, #13, #9, #48, #10, #53
- ADR: `docs/adr/adr-003-render-the-catalog-from-data-with-jinja2.md`
- Lessons: `docs/lessons/lesson-008-honest-urgency-over-invented-scarcity.md`

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
