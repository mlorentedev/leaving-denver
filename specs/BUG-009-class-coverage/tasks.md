---
tags: [spec, tasks, tests]
created: "2026-09-30"
---

# Tasks - BUG-009-class-coverage

## Setup

- [x] Branch `fix/unknown-tailwind-classes` from main 2759ab7; #103 In Progress
- [x] `proposal.md` complete

## PR 1

- [x] [AC2] Detector self-test (RED: helpers missing)
- [x] [AC1] [AC3] Coverage test over rendered pages, template sources, JS literals and class maps
- [x] [AC4] Utility assertions against the parsed class set
- [x] [AC5] Fail-closed test seeds a stale stylesheet
- [x] [AC6] `engines.node` in `package.json`
- [x] `make check` green; a deliberate typo shows RED

## Closing

- [ ] Independent adversarial review before archive
