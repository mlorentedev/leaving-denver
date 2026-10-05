---
id: "lesson-a-conflicting-pr-runs-no-ci"
type: lesson
scope: local
tags: [ci, github, review, process]
created: "2026-10-04"
source: "PR #181"
---

# Lesson: A Conflicting PR Runs No CI

## Context

The security-headers PR (#181) went up while three other PRs were landing. Its builder reported it
done: `make check` green locally in both modes, ready for review. Its checks showed CodeRabbit
(rate limited) and GitGuardian, both passing. The `test` job was not in the list at all.

## Finding

- `pull_request` workflows run on the PR's merge ref (`refs/pull/<n>/merge`). While the branch
  conflicts with the base, GitHub cannot build that ref, so it starts no run. No run means no red
  check either: the job is simply missing, and `gh pr checks` lists only the checks that did run.
- A list of green checks reads as "CI passed" unless someone counts which ones are there. Here the
  local run was real, but it predated the conflict: main had moved under the branch (#174, #175,
  #176), and the conflict was in a test file (`tests/test_smoke_script.py`).
- `gh pr view <n> --json mergeable` said `CONFLICTING`. That one field explains the missing run.

## Guard

None in code. The PR triage looks for the `test` check by name and reads `mergeable` before calling
a PR green. A missing required check is treated as a failure, not as nothing to report.

## Rule

Before calling a PR green, confirm that the check that matters ran on the current head, not just
that every listed check passed. If it is missing, look at `mergeable` first: a conflict starts no
CI at all.
