---
id: "lesson-an-unreadable-file-is-not-an-empty-one"
type: lesson
scope: local
tags: [secrets, sops, testing]
created: "2026-09-30"
source: "FEAT-004 (#16): recording postings in the encrypted file"
---

# Lesson: An Unreadable File Is Not an Empty One

## Context

`load_private()` returns `{}` when the sops file cannot be decrypted, which is right for the
build (CI has no key). The control panel needed to append to a posting history: read the list,
add a date, write it back.

## Finding

Built on `load_private()`, an append with a missing key would have read `{}`, found no history
and written a list of one, replacing the real one. Separately, `sops set` rejects a bare JSON
list on stdin ("Invalid --set value format") though objects and scalars work, and `sops
encrypt` looks for creation rules from the working directory upward, so a test in a temp dir
fails under a parent `.sops.yaml`.

While wiring `sold` to record the sale date, a test that stubbed everything but the recorder
ran the real `sops set` and wrote a bogus sale into `data/private.sops.yaml` (caught in
`git status`, reverted before any commit).

## Guard

`decrypt_private()` raises instead of returning `{}`; every writer reads through it, and
`test_nothing_is_written_when_the_history_cannot_be_read_first` fails if a `set` runs after a
failed read. A list grows by setting the next index (`...["facebook"][2]`). The real-binary
test runs against a throwaway age key and `cwd=tmp_path`, so the behaviour of sops itself is
checked, not a stub of it.

`tests/conftest.py` fails any test that calls `set_private` while `PRIVATE_SOPS_YAML` is still
the owner's real file (`test_a_test_that_forgets_to_stub_the_recorder_cannot_write_the_real_file`),
so the next forgotten stub is a red test, not an edited secret.
