---
tags: [spec, verification, images]
created: "2026-09-30"
---

# Verification - PERF-002-photo-freshness

## Evidence (PR A)

- [x] AC1 -> `test_a_replaced_source_with_an_older_mtime_is_rebuilt`
- [x] AC2 -> `test_a_settings_change_rebuilds_the_outputs`
- [x] AC3 -> `test_a_damaged_output_is_rebuilt_not_raised[empty jpeg|empty variant|garbage jpeg]`
- [x] AC4 -> `test_outputs_are_written_through_a_temporary_name`
- [x] AC5 -> `test_the_manifest_survives_a_rebuild_and_stays_out_of_public`, `test_up_to_date_outputs_are_not_rewritten`

## Test status

- `make check` -> 197 passed (ruff clean)
- Mutations, each caught by at least one test: freshness ignoring the digest (2 fail), `MAX_IMAGE_WIDTH` left out of the fingerprint (1 fail), variants checked for existence but not size (1 fail)
- `make build` writes `build/.photo-cache.json` (14 entries), outside the deployed `build/public`

## Decisions made during implementation

- One manifest per build, owned by `sync_all_photos`, passed to `process_image`. A default path would let the unit tests on `tmp_path` write into the real cache.
- The manifest is keyed by the output path under `build/public`, so moving the checkout costs nothing. For HEIC, the `.heic` source is hashed, not the ffmpeg intermediate.
- An entry is dropped before a rebuild and recorded after every output is in place. The manifest is saved once, at the end of the sync. A killed build leaves the previous manifest, whose fingerprint for a changed photo is already stale.
- The staged name is `<name>.tmp`, so it never matches the `<stem>-*w.webp` prune glob.

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-016-key-build-freshness-on-content-and-settings.md
- [x] ADR-worthy decision? no: a build-cache detail inside ADR-003's build, with no new dependency
- [x] New pattern candidate for `00_meta/patterns/`? no: single project so far
