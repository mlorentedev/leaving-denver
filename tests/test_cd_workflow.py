import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

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
