"""
scripts/prune-deployments.sh against a stubbed Cloudflare API (OPS-019): the dry run names every
deployment and writes nothing, `--apply` deletes everything but the alias holder, and the run
refuses rather than guesses when the keeper cannot be identified.

The stub also stands in for the credential's handling: it records each `curl` invocation, so a test
can fail if the token ever leaves the stdin config for the argument list, where `ps` shows it.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prune-deployments.sh"
pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None, reason="needs bash and jq"
)

TOKEN = "stub-token-value-never-echoed"

# `curl` as the script uses it: the Authorization header arrives in a config on stdin (`-K -`),
# the URL is the last argument. GET lists a page, DELETE removes one id.
CURL = textwrap.dedent(
    """\
    import json, os, sys
    state_path = os.environ["PRUNE_STATE"]
    state = json.load(open(state_path))
    argv = sys.argv[1:]
    stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    with open(os.environ["PRUNE_LOG"], "a") as log:
        log.write(json.dumps({"argv": argv, "stdin": stdin}) + "\\n")
    url = argv[-1]
    if not url.startswith("http"):
        sys.exit("stub: no url in %r" % (argv,))
    if "-X" in argv and argv[argv.index("-X") + 1] == "DELETE":
        dep = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if "force=true" not in url and state.get("requires_force", True):
            print('{"success":false,"errors":[{"code":8000035,"message":'
                  '"You cannot delete an aliased deployment without a `?force=true` parameter"}]}')
            sys.exit(22)
        if dep in state.get("fail_delete", []):
            print('{"success":false,"errors":[{"code":10405,"message":"Not Found"}]}')
            sys.exit(22)
        state.setdefault("deleted", []).append(dep)
        json.dump(state, open(state_path, "w"))
        print('{"success":true,"result":{}}')
        sys.exit(0)
    if "/deployments" not in url:
        print(json.dumps({"success": True, "errors": [],
                          "result": {"canonical_deployment":
                                     ({"id": state["canonical"]} if state.get("canonical")
                                      else None)}}))
        sys.exit(0)
    page = int(url.split("page=")[1].split("&")[0]) if "page=" in url else 1
    pages = state["pages"]
    body = {
        "success": True,
        "errors": [],
        "result": pages[page - 1] if page <= len(pages) else [],
        "result_info": {"page": page, "per_page": 25, "total_pages": len(pages)},
    }
    print(json.dumps(body))
    """
)


def deployment(dep_id, created, aliases=(), stage="success"):
    return {
        "id": dep_id,
        "created_on": created,
        "url": f"https://{dep_id}.leaving-denver.pages.dev",
        "aliases": list(aliases),
        "environment": "production" if "leaving-denver.pages.dev" in aliases else "preview",
        "latest_stage": {"name": "deploy", "status": stage},
    }


def project():
    """Four settled deployments in one page: two production builds, a candidate and an old
    preview. The project's canonical deployment is the second production build."""
    return {
        "canonical": "bbb222",
        "pages": [
            [
                deployment("aaa111", "2026-10-01T10:00:00Z"),
                deployment("bbb222", "2026-10-15T10:00:00Z", ["leaving-denver.pages.dev"]),
                deployment(
                    "ccc333", "2026-10-20T10:00:00Z", ["candidate.leaving-denver.pages.dev"]
                ),
                deployment("ddd444", "2026-10-05T10:00:00Z", ["feat-x.leaving-denver.pages.dev"]),
            ]
        ],
    }


def project_with_a_building_deployment():
    """The same project plus one still queued: its URL stays reachable, so the run must say so."""
    state = project()
    state["pages"][0].append(deployment("eee555", "2026-11-10T10:00:00Z", stage="active"))
    return state


def prune(tmp_path, state, apply=False, env=None, make=None):
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (tmp_path / "calls.jsonl").write_text("", encoding="utf-8")
    stub = tmp_path / "curl"
    stub.write_text(f"#!{sys.executable}\n{CURL}", encoding="utf-8")
    stub.chmod(0o755)
    environment = {
        **os.environ,
        "PRUNE_STATE": str(tmp_path / "state.json"),
        "PRUNE_LOG": str(tmp_path / "calls.jsonl"),
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "CLOUDFLARE_API_TOKEN": TOKEN,
        "CLOUDFLARE_ACCOUNT_ID": "76967f5ede1ce50efce34d90b7e94958",
        "CF_PROJECT": "leaving-denver",
        "CF_API": "https://api.cloudflare.test/client/v4",
        **(env or {}),
    }
    args = ["bash", str(SCRIPT)] + (["--apply"] if apply else [])
    if make:
        args = ["make", "-s", "prune-deployments", *make]
    result = subprocess.run(args, cwd=ROOT, env=environment, text=True, capture_output=True)
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    return result, calls


def deletes(calls):
    return [c["argv"][c["argv"].index("-X") + 1 :][1] for c in calls if "-X" in c["argv"]]


def deleted_ids(calls):
    found = []
    for call in calls:
        argv = call["argv"]
        if "-X" in argv and argv[argv.index("-X") + 1] == "DELETE":
            # the URL carries ?force=true: without it Cloudflare refuses an aliased deployment
            found.append(argv[-1].rstrip("/").rsplit("/", 1)[-1].split("?")[0])
    return found


def test_a_dry_run_names_every_deployment_and_writes_nothing(tmp_path):
    result, calls = prune(tmp_path, project())
    assert result.returncode == 0, result.stderr
    for dep in ("aaa111", "bbb222", "ccc333", "ddd444"):
        assert dep in result.stdout, dep
    keep = [line for line in result.stdout.splitlines() if line.startswith("keep")]
    assert len(keep) == 1 and "bbb222" in keep[0]
    assert deleted_ids(calls) == []
    assert "3 to delete" in result.stdout and "0 skipped" in result.stdout


def test_the_production_alias_holder_is_kept_and_the_rest_are_deleted(tmp_path):
    result, calls = prune(tmp_path, project(), apply=True)
    assert result.returncode == 0, result.stderr
    assert "bbb222" not in deleted_ids(calls)
    assert sorted(deleted_ids(calls)) == ["aaa111", "ccc333", "ddd444"]
    assert "--dry-run to review" not in result.stdout
    assert "3 deleted" in result.stdout


def test_every_delete_asks_for_force_so_an_aliased_preview_can_go(tmp_path):
    # Measured 2026-11-11: deleting the `candidate` deployment answers 400 (error 8000035)
    # without ?force=true, because it holds candidate.leaving-denver.pages.dev.
    result, calls = prune(tmp_path, project(), apply=True)
    assert result.returncode == 0, result.stderr
    urls = [c["argv"][-1] for c in calls if "-X" in c["argv"]]
    assert urls and all("force=true" in url for url in urls), urls


def test_an_ambient_apply_does_not_turn_a_dry_run_into_a_delete(tmp_path):
    # The mode comes from the flag alone. An APPLY exported into the calling shell for some other
    # tool must not delete 200+ deployments that the operator read as a simulation.
    for value in ("1", "true", "yes"):
        result, calls = prune(tmp_path, project(), env={"APPLY": value})
        assert result.returncode == 0, result.stderr
        assert deleted_ids(calls) == [], value
        assert "Nothing was deleted" in result.stdout


def test_the_make_target_rejects_any_apply_value_but_0_and_1(tmp_path):
    result, calls = prune(tmp_path, project(), make=["APPLY=false"])
    assert result.returncode != 0
    assert "APPLY must be empty, 0 or 1" in result.stderr
    assert calls == []


def test_a_deployment_still_building_is_skipped_and_the_run_says_so(tmp_path):
    # CodeRabbit's Major on #271: exiting 0 with a deployment skipped reports "done" over a list
    # with a live URL still in it. Exit 3 is the signal to run it again once the build settles.
    result, calls = prune(tmp_path, project_with_a_building_deployment(), apply=True)
    assert result.returncode == 3
    assert "eee555" not in deleted_ids(calls)
    assert "skip" in result.stdout and "eee555" in result.stdout
    assert "still building" in result.stderr and "run this again" in result.stderr


def test_a_failed_delete_stops_the_run_non_zero(tmp_path):
    state = project()
    state["fail_delete"] = ["aaa111"]
    result, calls = prune(tmp_path, state, apply=True)
    assert result.returncode == 1
    assert "aaa111" in result.stderr
    # the API's own message reaches the operator: that is the difference between "it failed" and
    # "it failed because the token lost Pages:Edit", which cost a second look on the first run.
    assert "Not Found" in result.stderr
    # it stops there: the failure is the last call, nothing is attempted after it
    assert deleted_ids(calls) == ["aaa111"]


def test_a_project_without_a_canonical_deployment_deletes_nothing(tmp_path):
    state = project()
    state["canonical"] = None
    result, calls = prune(tmp_path, state, apply=True)
    assert result.returncode != 0
    assert "canonical deployment" in result.stderr
    assert deleted_ids(calls) == []


def test_a_canonical_deployment_missing_from_the_list_deletes_nothing(tmp_path):
    # The two calls disagree about which project this is: deleting on that basis would either
    # delete every deployment or strand one.
    state = project()
    state["canonical"] = "zzz999"
    result, calls = prune(tmp_path, state, apply=True)
    assert result.returncode != 0
    assert "zzz999" in result.stderr
    assert deleted_ids(calls) == []


def test_pagination_is_followed(tmp_path):
    state = project()
    state["pages"].append([deployment("fff666", "2026-10-02T10:00:00Z")])
    result, calls = prune(tmp_path, state, apply=True)
    assert result.returncode == 0, result.stderr
    assert "fff666" in deleted_ids(calls)


def test_the_token_travels_on_stdin_and_never_on_argv(tmp_path):
    result, calls = prune(tmp_path, project(), apply=True)
    assert result.returncode == 0, result.stderr
    assert calls, "the script never called curl"
    for call in calls:
        assert TOKEN not in " ".join(call["argv"]), "the token reached the argument list"
        assert TOKEN in call["stdin"], "the token did not arrive in curl's config"
    assert TOKEN not in result.stdout and TOKEN not in result.stderr


@pytest.mark.parametrize("missing", ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"])
def test_a_missing_credential_refuses_to_start(tmp_path, missing):
    result, calls = prune(tmp_path, project(), env={missing: ""})
    assert result.returncode != 0
    assert missing in result.stderr
    assert calls == []
