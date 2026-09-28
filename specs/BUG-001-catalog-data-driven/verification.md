---
tags: [spec, verification, templates]
created: "2026-09-26"
---

# Verification - BUG-001-catalog-data-driven

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [x] AC1 -> `test_missing_marker_fails`
- [x] AC2 -> unpublished-item, private-draft and vehicle publish-flag contract tests
- [x] AC3 -> `test_undefined_field_fails_the_build`
- [x] AC4 -> bundle/page figure contract tests
- [x] AC5 -> `test_every_category_has_a_chip`
- [x] AC6 -> `test_no_unbacked_vehicle_claims`, `test_sale_schedule_comes_from_departure_date`, `test_drops_prints_windows_from_departure_date`, `test_vehicle_card_claims_are_in_data`
- [x] AC7 -> `test_payment_terms_by_kind`
- [ ] AC8 -> PR 5 preview measurement
- [ ] AC9 -> PR 6 localized build
- [ ] AC10 -> PR 4 copy budget passes; PR 5 sticky contact bar and four-fact sheet remain

## Test status

- Test suite: `uv run pytest` -> 53 passed
- Lint: `uv run ruff check .` -> passed; `uv run ruff format --check .` -> 39 files formatted
- Build: `uv run leaving-denver build` -> public and private outputs built; security verification passed
- Manual smoke test: pending PR 5 responsive preview check
- No regressions in existing test suite: yes

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- PR 2: `FileSystemLoader(TEMPLATES_DIR)` rather than `PackageLoader`, built per render so the contract tests can swap the templates dir. The templates still ship inside the package.
- PR 2: with Jinja2 a template that omits a variable renders fine, so the fail-closed marker became a post-render check that the page emits `const INVENTORY = <json>;` and `const _C = <json>;`.
- PR 2: `trim_blocks` and `lstrip_blocks` keep block tags from leaving blank lines, so wrapping the vehicle card still matched the golden page byte for byte.
- PR 2: besides the card, the `<title>`, the hero line and the car's payment sentence render only when a vehicle is published, so the page does not mention a car it does not show.
- PR 3: a free item keeps its `recommended_list_price` in the YAML, with `free_with_purchase: true`, so the private floors still check; the builder shows its note and counts it as $0 in bundle totals. That moved "take everything" from Save $173 to Save $153.
- PR 3: bundle cards, item cards and the take-everything card render server-side; `INVENTORY` stays in the page only for the item sheet.
- 2026-09-28: the owner published the car again; the card stays visible for now.
- PR 4: unconfirmed claims are removed rather than inferred. The page uses first-person singular voice, and vehicle claims render only from the sanitized YAML.
- PR 4: `departure_date` is the time SSOT. Both the public countdown and CLI drop windows derive from 2026-11-09.
- PR 4: seller data passed to Jinja is an explicit allowlist. A regression test proved that passing the full seller mapping would expose a newly added phone field to the template context.
- PR 4: Windows tests read generated HTML explicitly as UTF-8; relying on the platform default failed on typographic punctuation.

## Promotion candidates

Before archiving, flag what (if anything) should be promoted to the vault. If all three are "no", archive in repo is the only persistence.

- [x] Lesson for the repo's `docs/lessons/`? `lesson-012-template-contexts-are-public-data-contracts.md`
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: implementation guard within ADR-002's existing isolation boundary
- [x] New pattern candidate for `00_meta/patterns/`? no: one-project evidence

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/BUG-001-catalog-data-driven/` -> `specs/archive/BUG-001-catalog-data-driven/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
