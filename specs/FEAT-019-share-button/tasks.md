---
tags: [spec, tasks, templates]
created: "2026-10-06"
---

# Tasks - FEAT-019-share-button

## Setup

- [x] Branch created from main: `feat/share-button`
- [x] `proposal.md` is complete and acceptance criteria are testable
- [x] No open questions left in `proposal.md` "Risks / open questions"

## Implementation

- [x] [AC1] Item-sheet share tests expect the shared utm on `/` and `/es/` (failing first)
- [x] [AC2] Hero share tests: share, cancel, failed share, refused clipboard, Spanish (failing first)
- [x] [AC3] Drift test reads the catalog's shared source; fails without `share` in hit.js (mutation-checked)
- [x] [AC1, AC2] `shareLink` shared by the item sheet and the hero button; `SHARED` query on both
- [x] [AC3] `share` added to `SOURCES` in `functions/api/hit.js`

## Closing

- [x] Every acceptance criterion from `proposal.md` is covered by at least one test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes
- [x] No unrelated changes in the diff
- [x] `verification.md` filled in
- [x] PR opened referencing this spec folder
