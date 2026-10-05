"""scripts/verify-review-published.sh, the pr-agent guard, driven with a stub `gh`.

A review that did not happen must not report success (#1107). BUG #163: the guard's
contents read swallowed every API failure into "no review marker declared", a wrong
diagnosis — on 2026-10-03 a GitHub API outage made a published review report an
undeclared marker. The rules under test:

- a GitHub API failure is retried with backoff, and reported AS a failure, never
  as an undeclared marker;
- a genuinely absent entry still fails, naming the file and the refs checked;
- a published review passes; a missing one fails naming the NaN concurrency cause;
- the bootstrap fallback (entry only on the PR head) still works.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.skipif(
        sys.platform.startswith("win") and shutil.which("bash") is None,
        reason="runs the guard under bash",
    ),
    pytest.mark.skipif(shutil.which("jq") is None, reason="the stub serves jq-shaped JSON"),
]

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-review-published.sh"
# Resolved once, from the unmodified environment: inside run_guard the stub bin dir
# prepends to PATH, and on Windows scoop's BusyBox shim can shadow Git Bash there —
# a BusyBox bash cannot open a `C:/...` script path (#163's test harness, 2026-10-05).
BASH = shutil.which("bash")

MARKER = "## PR Reviewer Guide"
REGISTRY = json.dumps({"reviewers": [{"login": "github-actions", "review_markers": [MARKER]}]})
NOENTRY_REGISTRY = json.dumps({"reviewers": [{"login": "coderabbitai", "review_markers": ["x"]}]})
# A bot comment carrying the marker, updated after any STARTED the tests set.
REVIEW_COMMENTS = json.dumps(
    [
        {
            "user": {"login": "github-actions[bot]"},
            "updated_at": "2026-10-05T18:00:00Z",
            "body": f"{MARKER}\n\nHere are some key observations.",
        }
    ]
)

# A `gh` replacement scripted by env vars, recording every call it sees.
# CONTENTS_BEHAVIOR: "ok" | "timeout" (every read fails like an outage) |
# "flaky:N" (the first N reads fail, then serve the registry) | "noentry"
# (registry JSON without a github-actions entry).
# COMMENTS: "review" | "none".
STUB_GH = r"""#!/usr/bin/env bash
echo "$*" >> "$CALLS_FILE"
case "$*" in
  *"contents/harness/review-attestation.json"*)
    # Bootstrap PRs only: the PR head carries the registry entry before main does.
    if [ "${HEAD_HAS_ENTRY:-0}" = "1" ] && case "$*" in *"ref=$HEAD_SHA"*) true ;; *) false ;; esac; then
      printf '%s' "$REGISTRY" | base64; exit 0
    fi
    case "$CONTENTS_BEHAVIOR" in
      timeout) echo "gh: api.github.com: read timed out" >&2; exit 1 ;;
      flaky:*)
        n=${CONTENTS_BEHAVIOR#flaky:}
        if [ "$(cat "$SEEN_FILE")" -lt "$n" ]; then
          echo 1 >> "$SEEN_FILE"
          echo "gh: api.github.com: read timed out" >&2; exit 1
        fi
        ;&
      ok) printf '%s' "$REGISTRY" | base64 ;;
      noentry) printf '%s' "$NOENTRY_REGISTRY" | base64 ;;
    esac
    ;;
  *"pulls/"*)
    printf '%s' '"0123abcd0123abcd0123abcd0123abcd0123abcd"'
    ;;
  *"issues/"*"/comments"*)
    case "$COMMENTS" in
      review) printf '%s' "$REVIEW_COMMENTS" ;;
      none) printf '%s' '[]' ;;
    esac
    ;;
  *) echo "gh stub: unexpected call: $*" >&2; exit 64 ;;
esac
"""


def run_guard(
    tmp_path: Path, contents: str, comments: str, head_sha: str = "", head_has_entry: str = "0"
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "gh").write_text(STUB_GH, encoding="utf-8", newline="\n")
    (bin_dir / "gh").chmod(0o755)
    (tmp_path / "seen").write_text("0", encoding="utf-8")
    env = {
        **os.environ,
        "GH_TOKEN": "stub",
        "GITHUB_REPOSITORY": "mlorentedev/leaving-denver",
        "PR_NUMBER": "162",
        "BASE_REF": "main",
        "STARTED": "2026-10-05T17:00:00Z",
        "HEAD_SHA": head_sha,
        "HEAD_HAS_ENTRY": head_sha and head_has_entry,
        "RETRY_ATTEMPTS": "3",
        "RETRY_SLEEP_BASE": "0",  # the tests measure call counts, not wall clock
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "CALLS_FILE": str(tmp_path / "calls"),
        "SEEN_FILE": str(tmp_path / "seen"),
        "CONTENTS_BEHAVIOR": contents,
        "COMMENTS": comments,
        "REGISTRY": REGISTRY,
        "NOENTRY_REGISTRY": NOENTRY_REGISTRY,
        "REVIEW_COMMENTS": REVIEW_COMMENTS,
    }
    if sys.platform == "win32":
        # Run under Git Bash, which the repo's other shell tests also assume.
        return subprocess.run(
            [BASH, SCRIPT.as_posix()], capture_output=True, text=True, env=env, timeout=120
        )
    return subprocess.run([str(SCRIPT)], capture_output=True, text=True, env=env, timeout=120)


def contents_calls(tmp_path: Path) -> int:
    calls = tmp_path / "calls"
    if not calls.exists():
        return 0
    return sum(1 for line in calls.read_text(encoding="utf-8").splitlines() if "contents/" in line)


def test_a_published_review_passes(tmp_path):
    r = run_guard(tmp_path, contents="ok", comments="review")
    assert r.returncode == 0, r.stderr
    assert "review published" in r.stdout


def test_an_api_outage_is_reported_as_a_failure_not_as_an_undeclared_marker(tmp_path):
    """BUG #163: a timeout must never read as 'no review marker declared'. The ::error::
    lines go to stdout: that is where GitHub Actions reads them from."""
    r = run_guard(tmp_path, contents="timeout", comments="review")
    assert r.returncode == 1
    assert "GitHub API call failed" in r.stdout
    assert "no review marker declared" not in r.stdout


def test_the_contents_read_is_retried_before_anything_is_concluded(tmp_path):
    r = run_guard(tmp_path, contents="flaky:2", comments="review")
    assert r.returncode == 0, r.stdout
    assert contents_calls(tmp_path) == 3, "two failed reads plus the successful one"


def test_a_genuinely_undeclared_marker_still_fails_naming_the_file(tmp_path):
    r = run_guard(tmp_path, contents="noentry", comments="none")
    assert r.returncode == 1
    assert "no review marker declared" in r.stdout
    assert "review-attestation.json" in r.stdout


def test_a_missing_review_still_names_the_concurrency_cause(tmp_path):
    r = run_guard(tmp_path, contents="ok", comments="none")
    assert r.returncode == 1
    assert "published no review" in r.stdout
    assert "NaN concurrency" in r.stdout


def test_the_bootstrap_fallback_reads_the_entry_from_the_pr_head(tmp_path):
    r = run_guard(
        tmp_path, contents="noentry", comments="review", head_sha="0123abcd", head_has_entry="1"
    )
    assert r.returncode == 0, r.stderr
    assert "PR head" in r.stdout
