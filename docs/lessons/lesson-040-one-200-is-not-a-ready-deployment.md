# Lesson 040 — One 200 Is Not a Ready Deployment

**Date:** 2026-10-07
**Tags:** [ci, cloudflare, deploy, smoke, flaky]

## What happened

The deploy of #229 (CI run 37599450879) failed at "Smoke the candidate", so production stayed one build behind until the next merge deployed. The smoke's readiness loop saw `/` answer 200 and stopped waiting. The very next fetch of `/` got a 404 on every attempt for about 30 s, its whole retry budget. Minutes later the same deployment served every path. The step printed no `SMOKE FAIL` line, only curl's exit code 22, because the assignment `page=$(get "$url/")` had no `|| fail`.

## Why it matters

While a fresh Pages deployment propagates, edge nodes disagree: the same URL answers 200 from one and 404 from another. Readiness is a period of time, not a single moment, so a readiness check that stops at the first 200 proves nothing about the next request. This was the third failure of this kind, each found and fixed separately:

- Run 36810890186: a 404 seconds after a 200.
- #173: a 404 carrying the wrong body.
- #232: a 404 for 30 s after a 200.

Each earlier fix added retries to one fetch. None of them changed what "ready" means.

## Rule

- **Readiness is a streak, not a single success.** Wait for several consecutive 200s before any check that depends on what is served (`SMOKE_READY_STREAK`, 3 by default).
- **Derive the readiness budget from the same knobs as the retries** (`SMOKE_RETRIES`, `SMOKE_RETRY_DELAY`), so a test can shrink it and production can grow it.
- **Every fetch that can stop the script says what failed.** Under `set -e`, a bare command substitution exits with the tool's code and no message.
- **When a test stub models a flapping edge, make the flapping start where it started in reality.** Here that was after readiness, so the guard it protects (the policy read from the response curl kept) is still exercised.

## Related

- Issue #232; #173 and run 36810890186 (the earlier smoke races).
- `scripts/smoke.sh`, `tests/test_smoke_script.py` (`FLAPPING_HOME`, `flaky_after`).
