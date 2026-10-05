---
id: "lesson-a-skipped-deploy-is-not-a-failed-one"
type: lesson
scope: local
tags: [ci, github, deploy, testing, cloudflare]
created: "2026-10-04"
source: "PR #192 / issue #195"
---

# Lesson: A Skipped Deploy Is Not a Failed One

## Context

#192 (photo zoom in the catalog) merged. Its pull-request checks were green, three runs in a row.
The push to `main` then went red in the `test` job — and the site kept serving the previous build,
`b8581ce`, to every buyer for the next forty minutes. Nothing in the PR, and nothing on the board,
said the feature was not live.

## Finding

- **`deploy` is `needs: test`**, so a red `test` on `main` does not fail the deploy: it *skips* it.
  A skipped job is not in `gh pr checks` for the pull request, is not an email, and is not a red
  badge anywhere the author looks. Production is simply one build behind, silently.
- The `test` failure was a **false positive in a probabilistic check**:
  `tests/test_private_isolation.py::test_no_private_fixture_value_reaches_a_public_build` scans a
  *sealed* build for the fixture's numbers with `(?<![\w.-])VALUE(?![\w])`. The only content a
  sealed `seller/index.html` gains is the envelope — `salt`/`iv`/`ct`, **standard base64**, freshly
  random on every seal. A two-digit fixture value can land in those random characters flanked by
  `+`, `/` or a quote, which the regex accepts as boundaries. Measured: 300 fresh envelopes hold 15
  such tokens, the scan hunts 7 two-digit values → **about 1 red run in 260** (#195).
- So "it passed on the PR" was not evidence: the tree was identical (a squash of a rebased branch)
  and the check is a *draw*, not a function of the diff. Two local `make check` runs and three
  green PR runs said nothing about the fourth.
- The deployed build **names itself**: the footer carries `Build <sha>` from `GITHUB_SHA`. That one
  string is the difference between "CI was green" and "the change is live".

## Guard

- #195: carve the envelope out of the leak scan (it is ciphertext by construction), or scan the
  7-digit sentinels the other sealed tests use. The guard is not "retry until green": a retry hides
  the skip that matters.
- The deploy job runs `scripts/smoke.sh` against the deployment it just published, so a *deployed*
  build is checked. What nothing checks is whether the deploy job ran at all.

## Rule

A green pull request is not a deployed change. After merging, read the **push run of `main`** and
confirm the `deploy` job ran — `skipped` means production is behind, and says so nowhere. Then read
the footer's `Build <sha>` on the live site and match it to the merge commit.

Corollary: a test that scans random bytes is a probabilistic test. When it fails, ask what it
samples before believing the diff caused it — and when it passes, do not count it as a check.
