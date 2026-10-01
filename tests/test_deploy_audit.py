"""
scripts/audit-deploy.sh against a stubbed `gh` (CI-004): it passes on the settings
`make protect-deploy` and `make ci-secrets` leave, and fails on each kind of drift.
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
pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None, reason="needs bash and jq"
)

GH = textwrap.dedent(
    """\
    import json, os, subprocess, sys
    state = json.loads(open(os.environ["GH_AUDIT_STATE"]).read())
    args = sys.argv[1:]
    if args[:2] == ["secret", "list"]:
        if state["secrets"] is None:
            sys.exit("HTTP 403: Resource not accessible by integration")
        print("".join(f"{name}\\t2026-09-30\\n" for name in state["secrets"]), end="")
        sys.exit(0)
    assert args[0] == "api" and "-X" not in args, args  # read-only
    endpoint = next(a for a in args if a.startswith("repos/"))
    name = endpoint.split("/environments/")[1].split("/")[0]
    if name not in state["environments"]:
        sys.exit("HTTP 404: Not Found")
    environment = state["environments"][name]
    if endpoint.endswith("/deployment-branch-policies"):
        body = {"branch_policies": environment["policies"]}
    else:
        body = {"deployment_branch_policy": environment["policy"]}
    query = args[args.index("--jq") + 1]
    result = subprocess.run(["jq", "-r", query], input=json.dumps(body), text=True,
                            capture_output=True)
    print(result.stdout, end="")
    sys.exit(result.returncode)
    """
)


def expected():
    environment = {
        "policy": {"protected_branches": False, "custom_branch_policies": True},
        "policies": [{"id": 1, "name": "main", "type": "branch"}],
    }
    return {
        "environments": {"production": environment, "preview": json.loads(json.dumps(environment))},
        "secrets": ["SOME_OTHER_SECRET"],
    }


def audit(tmp_path, state):
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    stub = tmp_path / "gh"
    stub.write_text(f"#!{sys.executable}\n{GH}", encoding="utf-8")
    stub.chmod(0o755)
    env = {
        **os.environ,
        "GH_AUDIT_STATE": str(tmp_path / "state.json"),
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(
        ["bash", "scripts/audit-deploy.sh"], cwd=ROOT, env=env, text=True, capture_output=True
    )


def test_the_expected_settings_pass(tmp_path):
    result = audit(tmp_path, expected())
    assert result.returncode == 0, result.stderr
    assert "deploy audit OK" in result.stdout


def test_a_token_that_cannot_list_secrets_skips_only_that_check(tmp_path):
    state = expected()
    state["secrets"] = None
    result = audit(tmp_path, state)
    assert result.returncode == 0, result.stderr
    assert "skipped" in result.stdout


def drift(change):
    state = expected()
    change(state)
    return state


@pytest.mark.parametrize(
    "state, reason",
    [
        (drift(lambda s: s["environments"].pop("preview")), "preview is missing"),
        (
            drift(
                lambda s: s["environments"]["production"]["policies"].append(
                    {"id": 2, "name": "feature", "type": "branch"}
                )
            ),
            "production allows",
        ),
        (
            drift(lambda s: s["environments"]["preview"]["policies"][0].update(type="tag")),
            "preview allows: tag:main",
        ),
        (drift(lambda s: s["environments"]["preview"].update(policies=[])), "allows: nothing"),
        (
            drift(
                lambda s: s["environments"]["production"]["policy"].update(protected_branches=True)
            ),
            "not limited",
        ),
        (drift(lambda s: s["secrets"].append("SELLER_PHONE")), "SELLER_PHONE is still"),
        (
            drift(lambda s: s["secrets"].append("CLOUDFLARE_API_TOKEN")),
            "CLOUDFLARE_API_TOKEN is still",
        ),
    ],
)
def test_drift_fails_the_audit(tmp_path, state, reason):
    result = audit(tmp_path, state)
    assert result.returncode != 0
    assert reason in result.stderr
