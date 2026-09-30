---
tags: [spec, verification, images]
created: "2026-09-30"
---

# Verification - PERF-002-photo-freshness

## Evidence (PR A)

- [x] AC1 -> `test_a_replaced_source_with_an_older_mtime_is_rebuilt`
- [x] AC2 -> `test_a_settings_change_rebuilds_the_outputs[MAX_IMAGE_WIDTH|MAX_IMAGE_HEIGHT|JPEG_QUALITY|WEBP_QUALITY|VARIANT_WIDTHS]`
- [x] AC3 -> `test_a_damaged_output_is_rebuilt_not_raised[empty jpeg|empty variant|garbage jpeg]`
- [x] AC4 -> `test_outputs_are_written_through_a_temporary_name`, `test_a_failed_write_keeps_the_previous_outputs`, `test_a_killed_rebuild_never_leaves_a_fresh_entry`, `test_a_failed_heic_conversion_leaves_nothing_in_the_output_dir`
- [x] AC5 -> `test_the_manifest_survives_a_rebuild_and_stays_out_of_public`, `test_up_to_date_outputs_are_not_rewritten`

## Test status

- `make check` -> 204 passed (ruff clean)
- Mutations, each caught by at least one test: freshness ignoring the digest; each of the five settings left out of the fingerprint; the output stamps ignored (5 fail); no `.tmp` sweep; no cleanup of a staged file
- `make build` writes `build/.photo-cache.json` (14 entries), outside the deployed `build/public`

## Decisions made during implementation

- One manifest per build, owned by `sync_all_photos`, passed to `process_image`. A default path would let the unit tests on `tmp_path` write into the real cache.
- The manifest is keyed by the output path under `build/public`, so moving the checkout costs nothing. For HEIC, the `.heic` source is hashed, not the ffmpeg intermediate.
- An entry is recorded after every output is in place, with each output's size and mtime. The manifest is saved once, at the end of the sync. A killed build leaves the previous manifest, and its entries no longer match any output the killed build rewrote.
- The staged name is `<name>.tmp`, so it never matches the `<stem>-*w.webp` prune glob.

## Independent adversarial review of PR A (2026-09-30)

Reviewer: the `reviewer` subagent, not the implementer, read-only on 6033b61. Verdict: **PASS-WITH-GAPS**.

| # | Finding | Disposition |
|---|---|---|
| 1 | Major, reproduced: the in-memory `pop` never reached the saved manifest. Replace A with B, kill the build after B's JPEG, restore A, and A's entry vouched for B's JPEG. | **Applied.** Entries record each output's size and mtime, so any rewrite makes them stale. `test_a_killed_rebuild_never_leaves_a_fresh_entry` fails without the stamps (5 tests fail). |
| 2 | Major (tests): AC2 was proven for one setting of five | **Applied.** The test is parametrised over all five, and dropping any one from the fingerprint fails it. |
| 3 | Minor, reproduced: a failed ffmpeg left `<stem>.tmp.jpg` in the deployed tree | **Applied.** HEIC is decoded in a temporary directory outside `build/public`. The sync also sweeps stray `.tmp` files under `build/public/catalog`. |
| 4 | Minor: no test for a save failing midway | **Applied** (`test_a_failed_write_keeps_the_previous_outputs`). Removing the staged-file cleanup fails it. |
| 5 | Minor, theoretical: a JPEG truncated after its header counted as fresh | **Applied** through finding 1: a truncation changes the recorded size. |
| 6 | Nit: the encoder version is not in the fingerprint | **Applied** (`PIL.__version__`). Processing-code changes remain out: `make clean` covers them. |

## Promotion candidates

- [x] Lesson for the repo's `docs/lessons/`? yes: docs/lessons/lesson-016-key-build-freshness-on-content-and-settings.md
- [x] ADR-worthy decision? no: a build-cache detail inside ADR-003's build, with no new dependency
- [x] New pattern candidate for `00_meta/patterns/`? no: single project so far
