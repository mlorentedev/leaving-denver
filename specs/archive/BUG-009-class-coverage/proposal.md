---
id: "BUG-009-class-coverage"
type: spec
status: archived # draft | implementing | verifying | archived
review: waived
review_waived_reason: "Owner waived the launcher review on 2026-10-03: the repo has no harness/reviewer-pool.json, so dotf spec review cannot run. The owner chose an independent reviewer subagent instead; its verdict is in verification.md (Independent review, 2026-10-03)."
created: "2026-09-30"
issue: "mlorentedev/leaving-denver#103"   # repo#NNN — GitHub issue / Project item that tracks this spec
tags: [spec, proposal]
template_version: "1.0"
---

# BUG-009-class-coverage

## Why

<!-- from issue #103, raised by the independent BUG-003 review -->

Tailwind v4 compiles only the classes it recognises and drops the rest without a word. A typo such as `text-netural-500` builds cleanly, deploys to production and ships unstyled text, and nothing in `make check` notices. `tests/test_tailwind_build.py` checks only four hand-picked utilities, and it matches minified output byte for byte, so a Dependabot minor bump can turn it red without any regression. Its fail-closed test never seeds an old stylesheet, so it cannot prove what it claims. `package.json` does not state the Node version the CLI needs.

## What

1. **Class coverage test.** Every class token the pages use must have a rule in the stylesheet that ships with them, or be a named JS/CSS hook. The tokens come from:
   - the rendered public pages (EN and ES), built from the real inventory with an item Sold, one Pending and the vehicle Sold, so every Jinja branch and macro argument is rendered;
   - the static `class="..."` words of both templates, including the ones in JS template strings;
   - the string literals in `className =` and `classList.*(...)` statements, with their `${...}` ternary branches;
   - every JS class map (`STATUS_PILL`). Any class expression that is not literals, ternary branches, `+` joins or a registered map lookup fails the test (fail closed).
   Defined classes come from selector preludes only; declaration values, strings, `url()`s and comments define nothing.
   `make check` runs the test, and both the CI `test` job and `make deploy` require `make check`, so a missing class stops a deploy.
2. **A self-test for the detector:** a typo in a template string is reported, while a hook or a real utility is not.
3. **Robust utility assertions:** the four v4 utilities are checked as members of the parsed class set, not as minified bytes.
4. **Fail closed over a stale stylesheet:** the missing-CLI test seeds an old `styles.css` and asserts that the build still raises and leaves no half-written output.
5. **`engines`:** `package.json` states `node >=20`, the minimum for `@tailwindcss/cli` 4.

## Out of scope

- Checking arbitrary values such as `bg-[#123]`, beyond their presence as a rule.
- Class names built by string concatenation outside a registered map. The guard fails on those, so they cannot slip in.

## Acceptance criteria

- AC1: every class token used by `index.html` and `poster_assistant.html` has a CSS rule or is a declared hook.
- AC2: the detector reports a typo, and does not report hooks or real utilities.
- AC3: a JS class expression the detector cannot resolve (a variable, a call, an interpolation, an unregistered map) fails the test instead of being skipped.
- AC4: the v4 utility test no longer depends on minified byte order.
- AC5: a missing CLI raises even when an old `styles.css` exists, and the old file is left untouched.
- AC6: `package.json` declares `engines.node`.

<!-- archived 2026-10-03 — PR: https://github.com/mlorentedev/leaving-denver/pull/183 -->
