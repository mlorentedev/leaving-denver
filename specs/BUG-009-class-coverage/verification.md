---
tags: [spec, verification, tests]
created: "2026-09-30"
---

# Verification - BUG-009-class-coverage

## Evidence

- [x] AC1: `test_every_class_is_covered[index.html]` and `[poster_assistant.html]`
- [x] AC2: `test_detector_reports_a_typo_but_not_utilities_or_hooks`
- [x] AC3: `test_class_lookups_use_a_registered_map`, and `source_tokens` asserts that every indexed map is defined
- [x] AC4: `test_compiled_css_contains_v4_utilities` checks membership in the parsed class set
- [x] AC5: `test_missing_cli_fails_direct_build` seeds `.old{}` and asserts that it survives unchanged
- [x] AC6: `test_package_declares_the_node_it_needs` checks `engines.node` `>=20`, from `@tailwindcss/oxide`'s own `engines`

## Test status

- `make check`: 186 passed.
- Mutation check. With the build as is, a `zz-typo` injected in each context was reported by name:
  - a static attribute inside a Jinja `if`;
  - a Jinja branch that only renders for a Sold item;
  - a `photo()` macro argument that only renders for a Sold item;
  - `STATUS_PILL`;
  - a `${...}` ternary;
  - `classList.add`;
  - an `innerHTML` template string;
  - a `className` in the poster assistant.
  All 8 were caught, and the templates were restored afterwards.
- The current templates have zero gaps: every token maps to a rule, to the template's own `<style>`, or to one of seven declared hooks.

## Promotion candidates

- Lesson: yes: `docs/lessons/lesson-015-check-classes-against-the-compiled-css.md`
- ADR: no, no decision changed
- Pattern: no

## Archive checklist

- [ ] Independent review
- [ ] Status `archived`, folder moved, #103 closed with the PR link
