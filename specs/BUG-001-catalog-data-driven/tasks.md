---
tags: [spec, tasks]
created: "2026-09-26"
---

# Tasks - BUG-001-catalog-data-driven

> TDD order. One task = one focused commit. `[P]` = no dependency on an unchecked task; `[AC<n>]` = serves acceptance criterion n in `proposal.md`.
> One branch per PR, cut from `main` after the previous PR merges. Every PR runs `make check` green before it opens.

## Setup

- [x] Spec branch `spec/catalog-data-driven` with this folder and ADR-003
- [ ] `proposal.md` reviewed by the owner; open questions for PR 4 answered or explicitly dropped
- [x] #6 assigned and In Progress; #21 moved to Blocked on this spec

## Implementation

### PR 1: `fix/fail-closed-inventory-and-publish-flag` (closes #41)

- [ ] [AC1] `tests/test_build_contract.py::test_missing_inventory_marker_fails`: call `build_public_site` with a template lacking `__INVENTORY__`. Run `uv run pytest tests/test_build_contract.py -k marker`. Expected: FAIL, since today the build silently falls back.
- [ ] [AC1] In `src/leaving_denver/site_builder.py`, replace the two-regex injection with a `const INVENTORY = __INVENTORY__;` marker, and raise `RuntimeError` naming the marker when it is absent, as `__SELLER_CONTACT__` already does. Replace the placeholder array in `templates/index.html` with the marker. Expected: PASS.
- [ ] [P] [AC2] `test_unpublished_item_and_its_bundles_are_absent_from_public`: build from a fixture inventory (tmp copy via `monkeypatch` on `config` paths) with one item `published: false` and one bundle that contains it. Assert neither id occurs in any file under the public dir. Expected: FAIL.
- [ ] [AC2] `sanitize_public_inventory` drops items with `published: false` (default `true`) and every bundle that references one.
- [ ] [AC2] `test_unpublished_item_is_in_private_marked_draft`: the private `inventory.json` holds the item with `"draft": true`. The test skips when sops is not decryptable, like the other private tests.
- [ ] [AC2] `build_private_workspace` sets `draft: true` on unpublished items; `poster_assistant.html` shows a DRAFT tag for them.
- [ ] [AC2] `test_publish_flag_survives_yaml_round_trip`: `build_all` keeps `published: false` in `data/inventory.yaml` (guards BUG-006 #12).
- [ ] The car stays `published: true` in PR 1. Its card is hand-written HTML until PR 2, so the flag cannot remove it yet.

### PR 2: `refactor/render-catalog-with-jinja2` (closes #21)

- [ ] [AC3] `test_undefined_field_fails_the_build`: render a one-line template using `{{ item.titel }}` through the builder's environment. Expected: FAIL (there is no environment yet).
- [ ] [AC3] Add `jinja2` with `uv add jinja2`. Add `render(template, **ctx)` in `site_builder.py` using `Environment(loader=PackageLoader, undefined=StrictUndefined, autoescape=True)`. Expected: PASS.
- [ ] [AC3] `test_render_matches_previous_output`: a golden file of today's built `index.html` with the phone placeholder normalised. Render through Jinja2 and assert equality. This proves the swap changes nothing visible.
- [ ] [AC3] Convert `templates/index.html` to Jinja2: `{{ inventory_json | safe }}` for the marker, and `{{ contact_js | safe }}`. The template receives only the sanitized dict.
- [ ] [AC3] `tests/test_security_isolation.py`: add a check that the template context keys are exactly the sanitized ones, with no `firm_floor_price` and no private keys.
- [ ] [AC2] Wrap the vehicle card in `{% if vehicle %}` (`vehicle` = the published car, or `None`), then set `published: false` on the car. Test: no file under the public dir contains `2019-ford-escape`.
- [ ] Delete the golden-file test once PR 3 starts changing output. It exists only to prove the swap.

### PR 3: `fix/catalog-figures-from-data` (closes #6, bundle part of #32)

- [ ] [P] [AC4] `test_bundle_figures_come_from_items`: every bundle's `individual_total` equals the sum of its items' prices, and `savings` equals total minus `bundle_price`. Expected: FAIL (walnut and take-all are hand-typed).
- [ ] [AC4] Compute `individual_total` and `savings` in the builder; remove both keys from the YAML. Drop `bundle-walnut-suite`. Topper free with the sofa and airbed free with any purchase become bundle notes, owner-worded.
- [ ] [AC4] `test_rendered_page_figures_match_data`: parse `build/public/index.html` and assert the item count, each bundle's price and savings, and the whole-apartment total and savings against the computed values.
- [ ] [AC4] Render the bundle cards, the whole-apartment banner, the counts and the modal "Combine & save" box from `bundles` in Jinja2. Delete `UPSELL_MAP`; the client script looks up bundles by item id.
- [ ] [P] [AC5] `test_every_category_has_a_chip`: chips render from the set of item categories, so the build fails if a category is not in the ordered chip list in `site_builder.py`. Expected: FAIL today (`Living Room & Tech`).
- [ ] [AC5] Render the chips from data; fix the TV category.
- [ ] Remove the stray `</a>` in the modal's Close button, and the hardcoded modal status `Available` (render from `status`).

### PR 4: `fix/catalog-copy-from-data` (closes #13, #9, #48; needs the owner answers)

- [ ] [P] [AC6] `test_no_stale_or_unbacked_copy`: the `rg` from AC6 over `src/` and `data/` returns nothing. Expected: FAIL.
- [ ] [AC6] `seller.departure_date: 2026-11-09` replaces `moving_deadline`; the hero wording and countdown render from it; `leaving-denver drops` computes its drop dates from it (Oct 3–6, Oct 15–17, floors Oct 20–25, giveaway Nov 3–5) instead of fixed weeks.
- [ ] [AC6] `test_vehicle_card_claims_are_in_data`: every bullet on the rendered vehicle card is a `specs` entry, `odometer` or `title_status` of the car in the YAML.
- [ ] [AC6] Render the vehicle card from the car item: price, odometer, color and specs. Remove "highway", "factory remote start" and any claim the owner did not confirm.
- [ ] [P] [AC7] `test_payment_terms_by_kind`: the vehicle's rendered terms contain neither Venmo nor Zelle, and the page has no "no advance deposits" in the vehicle's context.
- [ ] [AC7] `seller.payment_methods` split into `household` and `vehicle`; the header and pickup copy render per kind; the deposit wording follows the owner's escrow decision.
- [ ] Apply the owner's voice choice and the style fixes from #48 ("one single" and the mixed voice).

### PR 5: `fix/mobile-horizontal-scroll` (closes #10)

- [ ] [AC8] Add `w-full` to the full-width sections and `shrink-0 whitespace-nowrap` to `.filter-btn`.
- [ ] [AC8] Check on the preview at 390 px that `document.documentElement.scrollWidth === 390`, and record the output in `verification.md`.

## Closing

- [ ] Every acceptance criterion from `proposal.md` is covered by at least one test
- [ ] Every acceptance criterion has a matching entry in `features.json` with a non-vacuous verification command
- [ ] Lint passes (`make lint`)
- [ ] No unrelated changes in any PR's diff
- [ ] `verification.md` filled in
- [ ] Independent adversarial review (`review.md`) before archive
