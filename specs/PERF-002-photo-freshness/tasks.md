---
tags: [spec, tasks, images]
created: "2026-09-30"
---

# Tasks - PERF-002-photo-freshness

## Setup

- [x] Branch `perf/content-keyed-photo-cache` from main 7f45fb9 (worktree `../leaving-denver-photos`)
- [x] `proposal.md` complete, acceptance criteria testable
- [x] #101 In Progress on the board

## Implementation (PR A)

- [x] [AC1] [AC2] [AC3] [AC4] [AC5] Failing tests: older-mtime replace, settings change, damaged outputs, temp-name writes, manifest round trip (RED: `process_image` takes no manifest)
- [x] [AC1] [AC2] `fingerprint` = sha256(source + output settings); `is_up_to_date` checks the manifest
- [x] [AC3] `output_width` treats an unreadable JPEG as missing; variants must be non-empty
- [x] [AC4] `save_atomically`: `<name>.tmp`, then `os.replace`
- [x] [AC5] `sync_all_photos` loads and saves `build/.photo-cache.json` (atomic)
- [x] Mutation check: dropping the digest, a setting, or the size check each fails a test

## Implementation (PR B)

- [x] [AC6] [AC7] Failing tests: `resolve_sizes`, per-(viewport, DPR) budget, 100vw self-check, DPR-3 hero, dialog `srcset` parsed from `INVENTORY` (RED: hero picks the JPEG; no 1600w variant)
- [x] [AC7] `VARIANT_WIDTHS` gains 1600; `w <= width` at all four sites; a variant as wide as the JPEG replaces it in `srcset`
- [x] lesson-013 states the DPR of each figure

## Closing

- [x] Every acceptance criterion of PR A is covered by a test
- [x] Every acceptance criterion has a matching entry in `features.json`
- [x] Lint passes (`make check`)
- [x] `verification.md` filled in for PR B
- [ ] Review findings dispositioned
- [ ] Independent adversarial review before archive
