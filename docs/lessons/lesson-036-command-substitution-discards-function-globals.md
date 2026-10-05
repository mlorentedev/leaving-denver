# Lesson 036 — Command Substitution Silently Discards a Function's Globals Under `set -u`

**Date:** 2026-10-05
**Tags:** [bash, ci, github-actions, testing, shell]

## What happened

While fixing BUG #163, `read_marker()` set two globals (`MARKER`, `API_FAILURE`) and was
invoked as `marker=$(read_marker "${BASE_REF}")`. Under `set -u`, the follow-up check
`[ -n "$API_FAILURE" ]` died with `unbound variable`: command substitution runs the
function in a **subshell**, so its assignments never reach the caller. Only stdout escapes.

## Why it matters

The failure is silent in review: the function "worked" (stdout carried the marker), and
the missing variable only surfaced in an environment where the code path actually ran.
The whole point of #163's fix was to carry API-failure state out of the read — exactly
the state the idiom discards.

## Rule

1. A bash function whose caller needs MORE than its stdout must be called bare
   (`read_marker "$ref"`), returning values through variables the caller reads.
2. When a rewrite moves logic out of a GitHub Actions step into a script, test the
   script's behavior with a stub CLI (`tests/test_review_guard.py`, stub `gh`) — the
   subshell scoping bug never showed up in the YAML, only under execution.
3. `mktemp` + stderr redirect captures a failed call's own error; a second API call to
   "read the error" doubles outage cost and can mask the failure (a finding by pr-agent).

## Related

- #163 (the guard fix), #201 (where the finding landed).
- `scripts/verify-review-published.sh` for the corrected shape.
