# Lesson 044 — A Test Only the Deploy Job Runs Is First Tested in Production

**Date:** 2026-11-10
**Tags:** [ci, testing, deploy, secrets, close-out]

## What happened

The merge that turned the site into the end page (`#268`, OPS-018) was green on the pull request
and **red in the deploy job**: one assertion, and the deploy stopped. Production kept serving the
catalog — the old page, with the phone number in it — for as long as it took to notice.

The test was `test_the_real_envelope_passes_validation_and_is_only_in_the_seller_page`. It is
skipped unless `SELLER_SEALED` is set (`"only the deploy job holds the real envelope"`), and the
deploy job is the only place that secret exists. So it ran for the first time on `main`, on the
first change that altered the shape of the build: with the sale over there is no `/seller/` to
hold the envelope, and `[] == ['seller/index.html']` failed.

Two earlier layers could have caught it and structurally could not:

- The `test` job has no secret, so the test skips.
- The `test-end-of-sale` job has no secret either, so it skips there too — the one job whose whole
  purpose is the end build.

## Why it matters

"CI is green" means *the jobs that ran* passed. A test gated on a production-only secret is not in
that set, so every assertion it makes about the built artefact is verified for the first time
against the thing that ships. Here the artefact that ships was a page that had stopped being
served, and the cost of the discovery was production serving a phone number that is being closed
on 2026-11-15.

The failure was also *good news in disguise*: the assertion was right in spirit and only wrong
about which build it was reading. What was missing was not a guard but a way for a pre-merge job
to run it.

## Rule

- **A test that reads the shipped artefact must be runnable before the merge.** If it needs a
  secret, synthesize the secret's *shape* instead: `seal_fixture()` produces a real envelope for a
  throwaway passphrase, and one test now builds both modes with one and asserts the invariant.
- **Synthesizing the secret is not enough if the expectation only exists in the deploy job.** The
  sibling test that already used a throwaway envelope built a *catalog* scratch — its helper drops
  the switch — so it could never have seen the end-mode expectation, and it passed while the
  deploy job failed. The expectation has to be **one definition** (`expected_envelope_holders`)
  that the pre-merge test and the deploy-only test both call; then a mode-blind assertion cannot
  exist in one of them only.
- **A test's expectation may depend on the build mode; the mode must be an input, not an
  assumption.** `[] if sale_is_over() else ["seller/index.html"]` is honest and checkable; a bare
  `["seller/index.html"]` is an assumption about a sale that is in progress.
- **When a job only runs on `main`, treat its first run as a code review of itself.** Either move
  the assertion earlier (a scratch build, a fixture, a synthetic secret) or accept, out loud, that
  production is where it gets tested.
- **Green on the PR is a claim about the jobs that ran.** Say which ones when it matters, and never
  merge a change that alters the shipped artefact's shape on the strength of a job that skipped the
  check that cares about it.
