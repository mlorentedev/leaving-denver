#!/usr/bin/env bash
# Delete every Cloudflare Pages deployment of one project except the one serving production
# (OPS-019, ADR-008): each deployment keeps its own permanent URL, and an old one still serves the
# catalog it was built from — with the phone number that closed on 2026-11-15 in it.
#
# Dry run unless --apply. The keeper is the project's `canonical_deployment` — the deployment the
# canonical domain answers with — and not "the newest" nor a match on `aliases` (the API returns
# `aliases: null` for a production deployment). When the project names no canonical deployment, or
# names one that is not in the deployment list, the run refuses and deletes nothing: this is the
# command that cannot be undone. A deployment whose build has not settled is skipped, so a deploy
# in flight survives the run.
#
# The token arrives in the environment (make pipes it from sops, as `make deploy` does) and reaches
# curl in a config on stdin, never on argv where `ps` would show it. Needs curl and jq.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: prune-deployments.sh [--dry-run|--apply]

  --dry-run   list what would be deleted, and delete nothing (the default)
  --apply     delete every deployment that is not serving production

Reads CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (both required), CF_PROJECT
(default leaving-denver), CF_API (override the API host; used by the tests) and
APPLY (any value but 0 applies; this is how `make prune-deployments APPLY=1`
reaches the script without GNU make's `$(if)`, which BusyBox make cannot parse).
EOF
}

mode=dry-run
case "${APPLY:-}" in
  "" | 0) ;;
  *) mode=apply ;;
esac
for arg in "$@"; do
  case "$arg" in
    --dry-run) mode=dry-run ;;
    --apply) mode=apply ;;
    -h | --help) usage; exit 0 ;;
    *)
      echo "prune-deployments: unknown argument $arg" >&2
      exit 2
      ;;
  esac
done

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is not set}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is not set}"
project="${CF_PROJECT:-leaving-denver}"
project_url="${CF_API:-https://api.cloudflare.com/client/v4}/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects/$project"
api="$project_url/deployments"

fail() {
  echo "prune-deployments: $*" >&2
  exit 1
}

# One API call, body on stdout. The token goes to curl on stdin; an HTTP error or a
# `success: false` answer is a failure, never a body the caller might read as a result.
call() {
  local method="$1" url="$2" body
  if [ -n "$method" ]; then
    body=$(printf 'header = "Authorization: Bearer %s"\n' "$CLOUDFLARE_API_TOKEN" |
      curl -sS --fail-with-body -X "$method" -K - "$url") || return 1
  else
    body=$(printf 'header = "Authorization: Bearer %s"\n' "$CLOUDFLARE_API_TOKEN" |
      curl -sS --fail-with-body -K - "$url") || return 1
  fi
  jq -e '.success == true' >/dev/null <<<"$body" || return 1
  printf '%s' "$body"
}

list="${TMPDIR:-/tmp}/prune-deployments.$$"
trap 'rm -f "$list"' EXIT

# The keeper: Cloudflare's own answer to "which deployment serves the canonical domain". A
# production deployment's `aliases` is null, so matching the alias finds nothing.
body=$(call "" "$project_url") || fail "cannot read the project $project"
keeper=$(printf '%s' "$body" | jq -r '.result.canonical_deployment.id // ""')
[ -n "$keeper" ] || fail "the project $project names no canonical deployment. Nothing was deleted"

page=1
while :; do
  body=$(call "" "$api?page=$page&per_page=25") || fail "cannot list deployments (page $page)"
  printf '%s' "$body" |
    jq -r '.result[] | [.id, (.latest_stage.status // "unknown")] | @tsv' >>"$list"
  total=$(printf '%s' "$body" | jq -r '.result_info.total_pages // 1')
  [ "$page" -lt "$total" ] || break
  page=$((page + 1))
done

[ -s "$list" ] || fail "the project $project has no deployments"
# A keeper missing from the list means the two calls disagree about which project this is, and
# deleting on that basis would delete every deployment or leave a stray one behind. Refuse.
if ! awk -F'\t' -v keeper="$keeper" '$1 == keeper { found = 1 } END { exit !found }' "$list"; then
  fail "the canonical deployment $keeper is not in the deployment list. Nothing was deleted"
fi

delete_now=0
skipped=0
while IFS=$'\t' read -r id stage; do
  if [ "$id" = "$keeper" ]; then
    printf 'keep    %s  %s\n' "$id" "$stage"
    continue
  fi
  case "$stage" in
    success | failure) ;;
    *)
      printf 'skip    %s  %s  (build in progress)\n' "$id" "$stage"
      skipped=$((skipped + 1))
      continue
      ;;
  esac
  printf 'delete  %s  %s\n' "$id" "$stage"
  delete_now=$((delete_now + 1))
done <"$list"

echo "---"
if [ "$mode" = dry-run ]; then
  echo "$delete_now to delete, $skipped skipped, 1 keep. Nothing was deleted: re-run with --apply"
  exit 0
fi

deleted=0
while IFS=$'\t' read -r id stage; do
  [ "$id" = "$keeper" ] && continue
  case "$stage" in
    success | failure) ;;
    *) continue ;;
  esac
  # ?force=true: Cloudflare refuses to delete a deployment that holds a branch alias
  # (error 8000035) — and every preview alias we want gone, `candidate` included, is one.
  # The keeper is never reached here, so the force cannot remove what production serves.
  call DELETE "$api/$id?force=true" >/dev/null ||
    fail "deleting $id failed after $deleted deleted: the rest were left alone"
  deleted=$((deleted + 1))
  echo "deleted $id"
done <"$list"

echo "---"
echo "$deleted deleted, $skipped skipped, 1 keep"
