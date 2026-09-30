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
