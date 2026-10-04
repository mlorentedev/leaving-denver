---
tags: [spec, verification, tests]
created: "2026-09-30"
---

# Verification - BUG-009-class-coverage

## Evidence

- [x] AC1: `test_every_class_is_covered[index.html]` and `[poster_assistant.html]`
- [x] AC2: `test_detector_reports_a_typo_but_not_utilities_or_hooks`, which also covers a single-quoted attribute and class names in declaration values, strings and `url()`s that must not count as defined
- [x] AC3: `test_detector_fails_closed_on_classes_it_cannot_read` covers six forms: a variable, a `${var}`, a call, an unregistered map, `classList.add(var)` and `setAttribute('class', var)`
- [x] AC4: `test_compiled_css_contains_v4_utilities` checks membership in the parsed class set
- [x] AC5: `test_missing_cli_fails_direct_build` seeds `.old{}` and asserts that it survives unchanged
- [x] AC6: `test_package_declares_the_node_it_needs` checks `engines.node` `>=20`, from `@tailwindcss/oxide`'s own `engines`

## Test status

- `make check`: 190 passed, after the CodeRabbit round.
- Mutation check. With the build as is, a `zz-typo` injected in each context was reported by name:
  - a static attribute inside a Jinja `if`;
  - a Jinja branch that only renders for a Sold item;
  - a `photo()` macro argument that only renders for a Sold item;
  - `STATUS_PILL`;
  - a `${...}` ternary;
  - `classList.add`;
  - an `innerHTML` template string;
  - a `className` in the poster assistant;
  - after the CodeRabbit round, a `+ (on ? ... : ...)` join.
  All 9 were caught. A `className = cls + '...'` was rejected as `Unresolved`. The templates were restored afterwards.
- The current templates have zero gaps: every token maps to a rule, to the template's own `<style>`, or to one of seven declared hooks.

## Independent review (2026-10-03)

The owner chose an independent reviewer subagent for these archives (the repo has no reviewer pool, so `dotf spec review` cannot run). The reviewer was not the implementer, worked read-only on main at 2cdc798, and ran the `features.json` commands plus the full suite on a clean copy (1042 passed, 2 skipped).

- Verdict: archive with a note. AC1-AC6 hold with their named tests.
- Superseded wording: AC1 names `poster_assistant.html`, which #146 deleted. Coverage now runs over `seller.html`, `sale_over.html`, `not_found.html`, `flyer.html` and `seller.mjs`.
- `features.json` f6 selected no test (`-k engines`); the archive PR points it at `test_package_declares_the_node_it_needs`.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-015-check-classes-against-the-compiled-css.md
- [x] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: no decision changed
- [x] New pattern candidate for `00_meta/patterns/`? no: one-project test guard

## Archive checklist

- [ ] Independent review
- [ ] Status `archived`, folder moved, #103 closed with the PR link
