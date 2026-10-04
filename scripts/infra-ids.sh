#!/usr/bin/env bash
# Read-only: find the ids of the Access identity provider, application and policy that were
# clicked in the dashboard, for the import blocks in infra/terraform/cloudflare/imports.tf
# (OPS-014). Prints `name = "id"` lines for ids.auto.tfvars and nothing else: never the
# token, never a policy body (it holds the owner's email). Needs CLOUDFLARE_API_TOKEN (set
# by `make infra-ids`), CF_ACCOUNT_ID, curl and jq; changes nothing.
set -euo pipefail

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is not set}"
: "${CF_ACCOUNT_ID:?CF_ACCOUNT_ID is not set}"
HOSTNAME_PART="${INFRA_IDS_HOST:-leaving-denver.pages.dev}"
API="${CF_API:-https://api.cloudflare.com/client/v4}/accounts/$CF_ACCOUNT_ID/access"

fail() { echo "infra-ids: $*" >&2; exit 1; }

# The token goes in a curl config on stdin, not on argv where `ps` would show it. Prints the
# body; returns non-zero, saying nothing, on an HTTP error or an unsuccessful answer.
get() {
  local body
  body=$(printf 'header = "Authorization: Bearer %s"\n' "$CLOUDFLARE_API_TOKEN" |
    curl -sS --fail-with-body -K - "$API/$1") || return 1
  jq -e '.success == true' >/dev/null <<<"$body" || return 1
  printf '%s' "$body"
}

# A token without Access scope is not refused on the lists: they come back empty, which
# reads as "nothing is configured". The organization endpoint is the honest probe: it
# answers 403 to such a token.
get organizations >/dev/null 2>&1 ||
  fail "this token cannot read Zero Trust Access (it needs Access: Organizations, Identity Providers and Groups: Read, and Access: Apps and Policies: Read)"

# Exactly one match, or stop: an import of the wrong object would later be "fixed" by apply.
only() { # <what> <ids...>
  local what=$1
  shift
  [ "$#" -eq 1 ] || fail "expected exactly one $what, found $#"
  printf '%s' "$1"
}

apps=$(get apps) || fail "could not list the Access applications"
app_id=$(only "Access application for $HOSTNAME_PART" $(jq -r --arg host "$HOSTNAME_PART" '
  .result[]
  | select(([.domain] + [.destinations[]?.uri] + (.self_hosted_domains // []))
           | any(. != null and startswith($host + "/seller")))
  | .id' <<<"$apps"))
policy_id=$(only "policy on that application" $(jq -r --arg app "$app_id" '
  .result[] | select(.id == $app) | .policies[]?.id' <<<"$apps"))
# imports.tf adopts the policy as a reusable one. A policy that is scoped to the application
# alone does not answer there, so say so now rather than at the import.
if reusable=$(get policies) && ! jq -e --arg id "$policy_id" 'any(.result[]; .id == $id)' >/dev/null <<<"$reusable"; then
  echo "infra-ids: warning: policy $policy_id is not a reusable policy (it is scoped to the application): make it reusable in the dashboard, or define it inline in access.tf and drop its import block" >&2
fi
idps=$(get identity_providers) || fail "could not list the identity providers"
idp_id=$(only "one-time PIN identity provider" $(jq -r '
  .result[] | select(.type == "onetimepin") | .id' <<<"$idps"))

printf 'access_idp_id    = "%s"\n' "$idp_id"
printf 'access_app_id    = "%s"\n' "$app_id"
printf 'access_policy_id = "%s"\n' "$policy_id"
