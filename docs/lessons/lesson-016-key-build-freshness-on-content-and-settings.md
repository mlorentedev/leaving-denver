---
id: "lesson-key-build-freshness-on-content-and-settings"
type: lesson
scope: local
tags: [build, images, testing]
created: "2026-09-30"
source: "PERF-002 (#101), raised by the independent PERF-001 review"
---

# Lesson: Key Build Freshness on Content and Settings

## Context

The photo sync skips a photo whose outputs look current, so local rebuilds stay fast.

## Finding

"Output newer than source" is not the same as "output made from this source". `mv`, `cp -p` and `rsync -t` carry the file's own timestamp, so a replaced photo can be older than the outputs of the one it replaced. A change to the quality or size settings touches no photo at all. In both cases the build is green and serves the old images. A zero-byte file left by a killed build passes an existence check, and the next build then crashes trying to open it.

## Guard

- Freshness is a fingerprint, sha256(source bytes + every setting that shapes the output), stored in a manifest outside the deployed tree (`build/.photo-cache.json`). Adding a setting means adding it to the fingerprint. `test_a_settings_change_rebuilds_the_outputs` shows why.
- An output that is unreadable or empty counts as missing, so it gets rebuilt and never raises.
- Every output is written to `<name>.tmp` and renamed into place. The manifest entry also records each output's size and mtime, so it vouches only for the files it saw written. The first version dropped the entry in memory before rebuilding, but a killed build never saved that drop. The saved entry for the old photo then vouched for the half-built new one once the old photo came back. The independent review reproduced it.
- Before trusting the check, break it (drop the digest, drop a setting, drop the size check) and watch a test fail.
