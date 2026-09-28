---
tags: [spec, verification, templates]
created: "2026-09-26"
---

# Verification - BUG-001-catalog-data-driven

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [ ] Criterion 1 -> commit `<hash>` / test `<name>`
- [ ] Criterion 2 -> commit `<hash>` / test `<name>`
- [ ] Criterion 3 -> commit `<hash>` / test `<name>`

## Test status

- Test suite: `<command> -> <output / coverage %>`
- Manual smoke test: what was exercised, what was observed
- No regressions in existing test suite: yes / no (if no, document)

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- PR 2: `FileSystemLoader(TEMPLATES_DIR)` rather than `PackageLoader`, built per render so the contract tests can swap the templates dir. The templates still ship inside the package.
- PR 2: with Jinja2 a template that omits a variable renders fine, so the fail-closed marker became a post-render check that the page emits `const INVENTORY = <json>;` and `const _C = <json>;`.
- PR 2: `trim_blocks` and `lstrip_blocks` keep block tags from leaving blank lines, so wrapping the vehicle card still matched the golden page byte for byte.
- PR 2: besides the card, the `<title>`, the hero line and the car's payment sentence render only when a vehicle is published, so the page does not mention a car it does not show.
- PR 3: a free item keeps its `recommended_list_price` in the YAML, with `free_with_purchase: true`, so the private floors still check; the builder shows its note and counts it as $0 in bundle totals. That moved "take everything" from Save $173 to Save $153.
- PR 3: bundle cards, item cards and the take-everything card render server-side; `INVENTORY` stays in the page only for the item sheet.
- 2026-09-28: the owner published the car again; the card stays visible for now.

## Promotion candidates

Before archiving, flag what (if anything) should be promoted to the vault. If all three are "no", archive in repo is the only persistence.

- [ ] Lesson for the repo's `docs/lessons/`? <yes / no - one line of what>
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? <yes / no - one line of what>
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. <yes / no - one line>

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/BUG-001-catalog-data-driven/` -> `specs/archive/BUG-001-catalog-data-driven/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
