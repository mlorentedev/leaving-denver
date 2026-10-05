#!/usr/bin/env bash
# A review that did not happen must not report success (#1107): PR-Agent swallows a
# failed inference into a clean exit, so this guard binds the job's verdict to a
# github-actions[bot] comment, updated since this run started, carrying the marker
# declared in harness/review-attestation.json.
#
# Extracted from the pr-agent workflow (a TOOL-013 port) so the diagnosis rules are
# testable with a stub gh (BUG #163, measured on run 37155990064): the GitHub API
# failing is a diagnosis of its own, never "the marker is undeclared", and a
# contents read is retried with backoff before anything is concluded.
#
# Env: GH_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, BASE_REF, STARTED, HEAD_SHA.
# Test knobs: RETRY_ATTEMPTS, RETRY_SLEEP_BASE (seconds, linear per-attempt backoff).
set -euo pipefail

ATTEMPTS=${RETRY_ATTEMPTS:-3}
SLEEP_BASE=${RETRY_SLEEP_BASE:-2}
FILE="harness/review-attestation.json"

read_marker() { # $1 = ref; sets MARKER ("" when the entry is absent) and API_FAILURE:
  # "" (every read answered), or the last attempt's own stderr. One gh call per attempt:
  # the failed call's stderr is captured to a temp file, never by re-calling the API
  # (a second call doubles an outage's cost and could answer, masking the failure).
  MARKER=""; API_FAILURE=""
  local ref=$1 attempt=1 content errfile
  errfile=$(mktemp)
  while [ "$attempt" -le "$ATTEMPTS" ]; do
    if content=$(gh api "repos/${GITHUB_REPOSITORY}/contents/${FILE}?ref=${ref}" \
                   --jq '.content' 2>"$errfile" | base64 -d 2>"$errfile"); then
      MARKER=$(printf '%s' "$content" | jq -r \
        '.reviewers[] | select(.login == "github-actions") | .review_markers[0] // empty' 2>/dev/null || true)
      rm -f "$errfile"
      return 0
    fi
    API_FAILURE=$(cat "$errfile")
    if [ "$attempt" -lt "$ATTEMPTS" ]; then
      sleep $((SLEEP_BASE * attempt))
      attempt=$((attempt + 1))
    else
      break
    fi
  done
  rm -f "$errfile"
  return 0
}

read_marker "${BASE_REF}"
marker=$MARKER
if [ -z "$marker" ] && [ -z "${HEAD_SHA:-}" ]; then
  # issue_comment events carry no pull_request payload; ask the API for the head.
  HEAD_SHA=$(gh api "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}" --jq '.head.sha' 2>/dev/null || true)
fi
if [ -z "$marker" ] && [ -n "${HEAD_SHA:-}" ]; then
  # The default branch has no github-actions entry yet: this is the PR that
  # introduces it. The head registry only proves the entry EXISTS; the marker
  # itself is PR-Agent's own heading, never text a PR could choose (a head-
  # supplied marker such as "#" would match any bot comment, CWE-345). Author
  # and start-stamp binding below still apply. Without this fallback the
  # bootstrap PR of every repository failed with a bare "exit code 1".
  base_api_failure=$API_FAILURE
  read_marker "${HEAD_SHA}"
  if [ -n "$MARKER" ]; then
    # The head read only proves the entry EXISTS. The marker itself stays PR-Agent's own
    # hardcoded heading, never text a PR could declare (a head-supplied marker such as " "
    # would match any bot comment — CWE-345; pr-agent flagged the regression on #201).
    marker="PR Reviewer Guide"
    echo "::notice::reviewer registry entry found only on the PR head;" \
      "using PR-Agent's own heading as the marker"
  fi
fi
if [ -z "$marker" ] || [ "$marker" = "null" ]; then
  if [ -n "$API_FAILURE" ] || [ -n "${base_api_failure:-}" ]; then
    # An outage reads as an empty marker; reporting "no marker declared" here sent a
    # real review to the wolves (BUG #163). Name the failure and the refs it hit.
    echo "::error::GitHub API call failed while reading ${FILE} (checked ${BASE_REF}" \
      "and the PR head); last error: ${API_FAILURE:-$base_api_failure}"
    echo "::error::If this was a transient outage, re-run the job once the API answers."
  else
    echo "::error::no review marker declared for github-actions in ${FILE}" \
      "(checked ${BASE_REF} and the PR head)"
  fi
  exit 1
fi
# --paginate emits one JSON array per page; `jq -s` slurps them into one
# array of arrays so the count spans every page (gh's own --slurp flag is
# not present on the runner's gh 2.46 and printed usage instead).
found=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments" --paginate \
  | jq -s --arg started "${STARTED}" --arg marker "${marker}" \
      '[.[][] | select(.user.login == "github-actions[bot]"
                       and (.updated_at >= $started)
                       and (.body | contains($marker)))] | length')
if [ "$found" -gt 0 ]; then
  echo "review published (marker: ${marker})"
  exit 0
fi
echo "::error::PR-Agent reported success but published no review" \
  "(no github-actions[bot] comment updated since ${STARTED} carries \"${marker}\")."
echo "::error::Most likely cause: NaN concurrency exhaustion — the cluster allows 5 simultaneous"
echo "::error::requests, shared with pi, qq and hive embeddings. See #1107."
exit 1
