---
tags: [spec, verification, templates]
created: "2026-09-30"
---

# Verification - CI-004-smoke-before-production

## Evidence

- [x] AC1 -> `test_production_smokes_a_candidate_before_it_deploys` asserts the order (candidate deploy, then its smoke, then the production deploy), that both candidate steps are production only, and that the production deploy is unconditional.
- [x] AC2 -> `test_the_canonical_site_is_smoked_after_the_production_deploy`: the last step smokes `https://leaving-denver.pages.dev` for production and the deployment URL for a preview.
- [x] AC3 -> `test_seller_phone_is_environment_scoped_by_ci_secrets`: the per-environment set comes before the repository-level delete, and no bare set is left.
- [x] AC4 -> `test_every_action_is_pinned_to_a_commit[ci.yml]` and `[deploy-audit.yml]`. Each SHA was resolved from its tag with `gh api` (annotated tags dereferenced): checkout v7.0.1, cache v6.1.0, setup-uv v7.6.0, setup-node v7.0.0, wrangler-action v4.1.3.
- [x] AC5 -> `tests/test_deploy_audit.py` (9 cases with a stubbed `gh`: expected settings, a token that cannot list secrets, and seven kinds of drift). Run against the live repository, it passes the environments and reports `SELLER_PHONE is still a repository secret: run make ci-secrets`. That is the expected state until the owner runs it.
- [x] AC6 -> `test_the_deploy_gate_refuses_the_test_placeholder` runs the gate's own script: the placeholder and an empty phone exit non-zero, and a real number exits 0.
- [x] AC7 -> `test_the_runbook_numbers_the_deploy_steps_and_names_the_candidate`.

## Test status

- Test suite: `make check` -> 312 passed, 1 skipped (the Windows-only collection test). `actionlint` is clean.
- Manual smoke test: the candidate path runs for the first time on this PR's merge to `main`; that run and the canonical smoke are checked after the merge.
- No regressions in existing test suite: yes

## Decisions made during implementation

- **One job, two deploys.** The candidate runs in the same job and environment as production, so it needs no second token and no second build. The Pages branch is `candidate`, which passes the branch-name check, so a dispatched preview can never take that name by accident.
- **The canonical site is smoked, not the production hash URL.** That is the address buyers use. The checks are invariants, so if the edge still serves the previous deployment for a moment, the smoke passes; the candidate smoke has already checked this build.
- **The secret check is local.** The workflow token cannot list repository secrets, so the scheduled audit checks the environments only, and `make audit-deploy` with the owner's `gh` checks both.

## Promotion candidates

- [ ] Lesson for the repo's `docs/lessons/`? no: the change applies the CI-003 review; the procedure lives in `docs/runbooks/ops.md`
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? no: it keeps the CI-003 deploy design and adds a gate in front of it
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. no: specific to this Pages project

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/CI-004-smoke-before-production/` -> `specs/archive/CI-004-smoke-before-production/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
