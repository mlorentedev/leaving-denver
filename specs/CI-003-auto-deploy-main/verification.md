---
tags: [spec, verification, templates]
created: "2026-09-29"
---

# Verification - CI-003-auto-deploy-main

## Evidence

Map every acceptance criterion from `proposal.md` to concrete proof (commit hash, test name, or observed behavior).

- [x] AC1 -> `test_main_push_deploys_production_only_after_tests` (workflow contract)
- [x] AC2 -> `test_manual_preview_and_guarded_main_redeploy`
- [x] AC3 -> `test_deploy_requires_real_phone_and_checks_public_site`
- [x] AC4 -> `test_docs_distinguish_auto_production_from_manual_preview`
- [x] AC5 -> `test_deploy_token_is_environment_scoped_and_branches_are_restricted`;
  GitHub API shows custom branch policies `["main"]` for both environments,
  environment-scoped tokens present and repository token absent.
- [ ] Live production deployment from a merged `main` push -> verify after merge.

## Test status

- Test suite: `make check` -> 92 passed, Ruff lint and format clean.
- Manual smoke test: pending the first post-merge push to production.
- No regressions in existing test suite: yes.

## Decisions made during implementation

Brief log of non-obvious trade-offs or course corrections taken during the work. Routine choices belong in commit messages, not here.

- A production push selects the `main` Pages branch and `production` environment;
  manual dispatch keeps its validated branch input. PR runs do not deploy.
- Fail closed when the real phone secret is missing, before building and uploading.
- A shell ref check cannot protect a repository-wide token against a modified
  branch workflow. Both deployment environments are limited to `main`, and the
  Pages token is only available as an environment-scoped secret.

## Promotion candidates

Answer each line `yes: <path>`, naming the file you promoted, or `no: <reason>`. `dotf spec archive` refuses a line left unanswered, a `no` without a reason, and a `yes` whose file does not exist; a `00_meta/` path is looked up in the vault.

- [ ] Lesson for the repo's `docs/lessons/`? <yes: path / no: reason>
- [ ] ADR-worthy decision for the repo's `docs/adr/adr-XXX.md`? <yes: path / no: reason>
- [ ] New pattern candidate for `00_meta/patterns/`? Only if this recurs in >1 project. <yes: path / no: reason>

## Archive checklist

- [ ] `proposal.md` frontmatter set to `status: archived`
- [ ] Folder moved: `specs/CI-003-auto-deploy-main/` -> `specs/archive/CI-003-auto-deploy-main/`
- [ ] Bitácora board ticket for this spec moved to Done / closed with PR link (ADR-018)
- [ ] Promotions above executed (if any)
