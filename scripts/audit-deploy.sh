#!/usr/bin/env bash
# Read-only check of the deploy settings `make protect-deploy` and `make ci-secrets` set
# (CI-004): both environments allow only the branch `main`, and no deploy secret is left
# where a workflow outside them can read it. Needs `gh`; changes nothing.
set -euo pipefail

fail=0
problem() { echo "AUDIT FAIL: $*" >&2; fail=1; }

for environment in production preview; do
  if ! settings=$(gh api "repos/{owner}/{repo}/environments/$environment" \
    --jq '.deployment_branch_policy | "\(.protected_branches) \(.custom_branch_policies)"'); then
    problem "environment $environment is missing or unreadable"
    continue
  fi
  [ "$settings" = "false true" ] || problem "$environment is not limited to its branch policies ($settings)"
  policies=$(gh api --paginate "repos/{owner}/{repo}/environments/$environment/deployment-branch-policies" \
    --jq '.branch_policies[] | "\(.type):\(.name)"' | sort)
  [ "$policies" = "branch:main" ] || problem "$environment allows: ${policies:-nothing}"
done

# The workflow's token cannot list secrets; the owner's can, so this part runs locally.
if secrets=$(gh secret list 2>/dev/null); then
  for name in CLOUDFLARE_API_TOKEN SELLER_PHONE SELLER_SEALED; do
    if grep -q "^$name[[:space:]]" <<<"$secrets"; then
      problem "$name is still a repository secret: run make ci-secrets"
    fi
  done
else
  echo "deploy audit: this token cannot list repository secrets, so that check is skipped"
fi

# SELLER_SEALED (ADR-007) belongs to both environments. A missing one is a warning, not a
# failure: the secret is set by `make ci-secrets`, and a build without it only has no /seller/ data.
for environment in production preview; do
  if listed=$(gh secret list --env "$environment" 2>/dev/null); then
    grep -q "^SELLER_SEALED[[:space:]]" <<<"$listed" ||
      echo "deploy audit: warning: SELLER_SEALED is not set in $environment: run make ci-secrets" >&2
  fi
done

[ "$fail" = 0 ] || exit 1
echo "deploy audit OK"
