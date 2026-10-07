#!/bin/sh
# Run one Terraform subcommand against infra/terraform/cloudflare with the credentials it needs
# (OPS-014, ADR-012): `scripts/tf-run.sh plan -input=false -out=plan.tfplan`. It was a `define`
# block in the Makefile until BusyBox make, which has no `define`, could not parse the file
# (lesson-035). POSIX sh, so it runs the same under dash, bash and BusyBox ash.
#
# Both secrets are read into shell variables first, so a failed `sops` stops the run instead
# of leaving an empty value behind. They reach Terraform in its environment only: never on
# argv, never to stdout. The Makefile passes TF_DIR, TF_TOKEN_KEY, SOPS_FILE and CF_ACCOUNT_ID
# (the account id is not a secret); every argument here is Terraform's own.
set -eu

: "${TF_DIR:?TF_DIR is not set}"
: "${TF_TOKEN_KEY:?TF_TOKEN_KEY is not set}"
: "${SOPS_FILE:?SOPS_FILE is not set}"
: "${CF_ACCOUNT_ID:?CF_ACCOUNT_ID is not set}"

token="$(sops -d --extract "[\"$TF_TOKEN_KEY\"]" "$SOPS_FILE")" || {
  echo "no $TF_TOKEN_KEY in $SOPS_FILE: make secrets" >&2
  exit 1
}
email="$(sops -d --extract '["owner_email"]' "$SOPS_FILE")" || {
  echo "no owner_email in $SOPS_FILE: make secrets" >&2
  exit 1
}
if [ -z "$token" ] || [ -z "$email" ]; then
  echo "empty Terraform token or owner_email" >&2
  exit 1
fi

# Exported, then exec'd: the secrets live only in this process and the terraform that replaces it.
CLOUDFLARE_API_TOKEN="$token"
TF_VAR_owner_email="$email"
TF_VAR_account_id="$CF_ACCOUNT_ID"
export CLOUDFLARE_API_TOKEN TF_VAR_owner_email TF_VAR_account_id
exec terraform -chdir="$TF_DIR" "$@"
