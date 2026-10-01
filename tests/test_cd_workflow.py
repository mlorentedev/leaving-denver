import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.load(
    (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
    Loader=yaml.BaseLoader,
)
DEPLOY = WORKFLOW["jobs"]["deploy"]
BRANCH = "${{ github.event_name == 'push' && 'main' || inputs.branch }}"


def test_main_push_deploys_production_only_after_tests():
    assert WORKFLOW["on"]["push"]["branches"] == ["main"]
    assert DEPLOY["needs"] == "test"
    assert DEPLOY["if"] == (
        "(github.event_name == 'push' && github.ref == 'refs/heads/main')"
        " || github.event_name == 'workflow_dispatch'"
    )
    assert DEPLOY["environment"]["name"] == (
        "${{ github.event_name == 'push' && 'production' "
        "|| inputs.branch == 'main' && 'production' || 'preview' }}"
    )
    assert DEPLOY["concurrency"]["group"] == f"pages-{BRANCH}"


def test_manual_preview_and_guarded_main_redeploy():
    assert WORKFLOW["on"]["workflow_dispatch"]["inputs"]["branch"]["default"] == "preview"
    validation = next(
        step for step in DEPLOY["steps"] if step.get("name") == "Validate branch input"
    )
    assert validation["env"]["BRANCH"] == BRANCH
    assert "refs/heads/main" in validation["run"]
    assert "branch=main must be dispatched from main" in validation["run"]
    deployment = next(step for step in DEPLOY["steps"] if step.get("id") == "deploy")
    assert deployment["with"]["command"].endswith(f"--branch={BRANCH}")


def test_deploy_requires_real_phone_and_checks_public_site():
    assert DEPLOY["env"]["SELLER_PHONE"] == "${{ secrets.SELLER_PHONE }}"
    assert any(
        "SELLER_PHONE" in step.get("run", "") and "exit 1" in step.get("run", "")
        for step in DEPLOY["steps"]
    )
    commands = [step.get("run", "") for step in DEPLOY["steps"]]
    assert "make check" in commands
    assert any("scripts/smoke.sh" in cmd for cmd in commands)
    assert (ROOT / "wrangler.toml").read_text(encoding="utf-8").find(
        'pages_build_output_dir = "build/public"'
    ) >= 0


def test_docs_distinguish_auto_production_from_manual_preview():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    operations = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8").lower()
    assert "automatically" in readme and "preview" in readme
    assert "automatically" in operations and "preview" in operations


def test_deploy_token_is_environment_scoped_and_branches_are_restricted():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    policy = (ROOT / ".github/deployment-environment.json").read_text(encoding="utf-8")
    assert '"custom_branch_policies": true' in policy
    assert "protect-deploy:" in makefile
    assert "deployment-branch-policies" in makefile
    assert "gh secret set CLOUDFLARE_API_TOKEN --env" in makefile
    assert "gh secret delete CLOUDFLARE_API_TOKEN" in makefile
    assert "make ci-secrets" in (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")


def test_deploy_protection_removes_stale_policies_and_is_idempotent(tmp_path):
    state_file = tmp_path / "policies.json"
    initial = {
        "production": [
            {"id": 1, "name": "preview", "type": "branch"},
            {"id": 2, "name": "old-tag", "type": "tag"},
        ],
        "preview": [
            {"id": 3, "name": "main", "type": "branch"},
            {"id": 4, "name": "main", "type": "tag"},
        ],
        "writes": [],
    }
    state_file.write_text(json.dumps(initial), encoding="utf-8")
    stub = tmp_path / "gh"
    stub.write_text(
        "#!"
        + sys.executable.replace("\\", "/")
        + "\n"
        + textwrap.dedent(
            """\
            import json
            import os
            import subprocess
            import sys
            from pathlib import Path

            path = Path(os.environ["GH_POLICY_STATE"])
            data = json.loads(path.read_text(encoding="utf-8"))
            args = sys.argv[1:]
            if not args or args[0] != "api":
                raise SystemExit("unexpected gh command: " + repr(args))
            endpoint = next((arg for arg in args if "/environments/" in arg), "")
            environment = next((e for e in ("production", "preview") if f"/{e}" in endpoint), None)
            if environment is None:
                raise SystemExit("missing environment")
            operation = args[args.index("-X") + 1] if "-X" in args else "GET"
            if operation == "GET":
                if "--paginate" not in args:
                    raise SystemExit("branch policy listing must paginate")
                query = args[args.index("--jq") + 1]
                policies = data[environment]
                for page in (policies[:1], policies[1:]):
                    result = subprocess.run(
                        ["jq", "-r", query],
                        input=json.dumps({"branch_policies": page}),
                        text=True, capture_output=True,
                    )
                    if result.returncode:
                        raise SystemExit(result.stderr)
                    print(result.stdout, end="")
            elif operation == "PUT":
                data["writes"].append(["PUT", environment])
            elif operation == "DELETE":
                policy_id = int(endpoint.rsplit("/", 1)[-1])
                data[environment] = [p for p in data[environment] if p["id"] != policy_id]
                data["writes"].append(["DELETE", environment, policy_id])
            elif operation == "POST":
                assert "-f" in args and "name=main" in args and "type=branch" in args
                data[environment].append({"id": 5, "name": "main", "type": "branch"})
                data["writes"].append(["POST", environment])
            else:
                raise SystemExit("unexpected operation: " + operation)
            path.write_text(json.dumps(data), encoding="utf-8")
            """
        ),
        encoding="utf-8",
    )
    stub.chmod(0o755)
    env = {**os.environ, "GH_POLICY_STATE": str(state_file)}
    env["PATH"] = str(tmp_path) + os.pathsep + env["PATH"]

    for _ in range(2):
        result = subprocess.run(
            ["make", "protect-deploy"], cwd=ROOT, env=env, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stderr
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert [p["name"] for p in state["production"]] == ["main"]
        assert [p["type"] for p in state["preview"]] == ["branch"]

    assert state["writes"] == [
        ["PUT", "production"],
        ["DELETE", "production", 1],
        ["DELETE", "production", 2],
        ["POST", "production"],
        ["PUT", "preview"],
        ["DELETE", "preview", 4],
        ["PUT", "production"],
        ["PUT", "preview"],
    ]


def test_local_pages_commands_preserve_sops_shell_substitution():
    result = subprocess.run(
        ["make", "-n", "cf-project"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert 'CLOUDFLARE_API_TOKEN="$(sops -d --extract' in result.stdout
    assert 'CLOUDFLARE_API_TOKEN=""' not in result.stdout


# CI-004: production deploys smoke a candidate first, and the trust surface around the token
# is narrower.
CANONICAL = "https://leaving-denver.pages.dev"
PRODUCTION_ONLY = "env.PRODUCTION == 'true'"


def step_index(predicate):
    return next(i for i, step in enumerate(DEPLOY["steps"]) if predicate(step))


def test_production_smokes_a_candidate_before_it_deploys():
    assert DEPLOY["env"]["PRODUCTION"] == (
        "${{ github.event_name == 'push' || inputs.branch == 'main' }}"
    )
    candidate = step_index(lambda s: s.get("id") == "candidate")
    candidate_smoke = step_index(lambda s: "steps.candidate.outputs" in str(s.get("env", "")))
    production = step_index(lambda s: s.get("id") == "deploy")
    assert candidate < candidate_smoke < production
    steps = DEPLOY["steps"]
    assert steps[candidate]["with"]["command"].endswith("--branch=candidate")
    assert "scripts/smoke.sh" in steps[candidate_smoke]["run"]
    # A dispatched preview deploys once: both candidate steps are production only.
    assert steps[candidate]["if"] == PRODUCTION_ONLY
    assert steps[candidate_smoke]["if"] == PRODUCTION_ONLY
    assert "if" not in steps[production]
    assert steps[candidate_smoke]["run"] == 'scripts/smoke.sh "$DEPLOYMENT_URL"'


def test_no_deploy_step_can_fail_without_failing_the_job():
    # continue-on-error on the candidate smoke would publish a build that failed it.
    loose = [
        s.get("name", s.get("id", s.get("uses")))
        for s in DEPLOY["steps"]
        if "continue-on-error" in s
    ]
    assert not loose
    assert "continue-on-error" not in DEPLOY


def test_the_canonical_site_is_smoked_after_the_production_deploy():
    production = step_index(lambda s: s.get("id") == "deploy")
    final = DEPLOY["steps"][-1]
    assert DEPLOY["steps"].index(final) > production
    assert "scripts/smoke.sh" in final["run"]
    target = final["env"]["DEPLOYMENT_URL"]
    assert target == (
        f"${{{{ env.PRODUCTION == 'true' && '{CANONICAL}' "
        "|| steps.deploy.outputs.deployment-url }}"
    )


def run_contact_gate(phone):
    gate = next(s for s in DEPLOY["steps"] if s.get("name") == "Require production contact")
    return subprocess.run(
        ["bash", "-c", gate["run"]],
        env={**os.environ, "SELLER_PHONE": phone},
        capture_output=True,
        text=True,
    )


def test_the_deploy_gate_refuses_the_test_placeholder():
    placeholder = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))[
        "jobs"
    ]["test"]["env"]["SELLER_PHONE"]
    assert run_contact_gate(placeholder).returncode != 0
    assert run_contact_gate("").returncode != 0
    assert run_contact_gate("(555) 555-0100").returncode != 0
    assert run_contact_gate("+1 555-555-0100").returncode != 0
    assert run_contact_gate("+13035550123").returncode == 0


def test_seller_phone_is_environment_scoped_by_ci_secrets():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile[makefile.index("ci-secrets:") : makefile.index("protect-main:")]
    scoped = recipe.index("gh secret set SELLER_PHONE --env")
    removed = recipe.index("gh secret delete SELLER_PHONE")
    # The repository-level secret goes only once every environment has its own.
    assert scoped < removed
    # A failed listing must stop the recipe, not read as "no such secret" and skip the delete.
    assert "gh secret list |" not in recipe
    assert "gh secret set SELLER_PHONE\n" not in recipe
    assert "gh secret set SELLER_PHONE;" not in recipe


@pytest.mark.parametrize("workflow", ["ci.yml", "deploy-audit.yml"])
def test_every_action_is_pinned_to_a_commit(workflow):
    lines = (ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8").splitlines()
    uses = [line.strip() for line in lines if line.strip().lstrip("- ").startswith("uses:")]
    assert uses
    for line in uses:
        assert re.fullmatch(r"(- )?uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", line), line


def test_the_runbook_numbers_the_deploy_steps_and_names_the_candidate():
    operations = (ROOT / "docs/runbooks/ops.md").read_text(encoding="utf-8")
    deploy = operations[operations.index("## Deploy and roll back") :]
    deploy = deploy[: deploy.index("\n## ", 1)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", deploy, flags=re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert "candidate" in deploy


# FEAT-009 PR 2 (ADR-007): the deploy carries the sealed private data, and refuses to go out
# without it, the way it refuses to go out without the real phone.
def test_deploy_requires_the_sealed_private_data_before_building():
    assert DEPLOY["env"]["SELLER_SEALED"] == "${{ secrets.SELLER_SEALED }}"
    gate = step_index(
        lambda s: "SELLER_SEALED" in s.get("run", "") and "exit 1" in s.get("run", "")
    )
    first_build = step_index(lambda s: s.get("run") == "make check")
    assert gate < first_build, "the gate must stop the job before it builds anything"
    script = DEPLOY["steps"][gate]["run"]
    # An empty secret (the one that was never set arrives empty) must fail the step. The gate
    # is run here, as the runner would, against an empty and a set value.
    for value, expected in (("", 1), ("   ", 1), ('{"v":1}', 0)):
        result = subprocess.run(
            ["bash", "-c", script],
            env={**os.environ, "SELLER_SEALED": value},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == expected, (value, result.stdout, result.stderr)
    refused = subprocess.run(
        ["bash", "-c", script],
        env={**os.environ, "SELLER_SEALED": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert "SELLER_SEALED" in refused.stdout


def test_the_test_job_builds_without_the_sealed_secret():
    """Every PR and the test job show "No private data in this build"."""
    assert "SELLER_SEALED" not in WORKFLOW["jobs"]["test"].get("env", {})
    assert "SELLER_SEALED" not in str(WORKFLOW["jobs"]["test"]["steps"])


def test_the_workflow_never_prints_the_sealed_secret():
    for step in DEPLOY["steps"]:
        run = step.get("run", "")
        if "SELLER_SEALED" in run:
            assert "echo \"$SELLER_SEALED" not in run
            assert "echo $SELLER_SEALED" not in run
            assert "cat" not in run.split()
