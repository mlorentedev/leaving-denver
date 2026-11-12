"""PR-Agent runs from the shared ci-workflows job: this repo pins the caller and keeps only
its own review instructions. The model chain and token budgets are the shared job's, set
through the environment, which sits above .pr_agent.toml, so a copy left in the toml
would only drift from what actually runs."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/pr-agent.yml"
SHARED = re.compile(
    r"^\s+uses: mlorentedev/ci-workflows/\.github/workflows/pr-agent\.yml@[0-9a-f]{40} # v\d+\.\d+\.\d+$",
    re.MULTILINE,
)
SHARED_KEYS = {
    "model",
    "model_weak",
    "fallback_models",
    "custom_model_max_tokens",
    "max_model_tokens",
    "ai_timeout",
    "reasoning_effort",
    "publish_output_progress",
    "max_output_tokens",
}


def test_the_workflow_calls_the_shared_job_pinned_by_sha():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert len(SHARED.findall(workflow)) == 1
    assert "The-PR-Agent/pr-agent" not in workflow


def test_the_toml_leaves_the_model_chain_to_the_shared_job():
    toml = tomllib.loads((ROOT / ".pr_agent.toml").read_text(encoding="utf-8"))
    assert not SHARED_KEYS & set(toml.get("config", {}))
    assert "github_action_config" not in toml
