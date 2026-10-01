"""PR-Agent's model chain: the workflow env and .pr_agent.toml name the same models
(the env wins, the toml is what the default branch reads), and no retired model."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED = {"openai/mimo-v2.5"}  # NaN retired it 2026-09-30: 401 (dotfiles AI-045, #1763)


def chains():
    toml = tomllib.loads((ROOT / ".pr_agent.toml").read_text(encoding="utf-8"))["config"]
    workflow = (ROOT / ".github/workflows/pr-agent.yml").read_text(encoding="utf-8")
    model = re.search(r"CONFIG__MODEL: (\S+)", workflow).group(1)
    fallbacks = json.loads(re.search(r"CONFIG__FALLBACK_MODELS: '([^']+)'", workflow).group(1))
    return [toml["model"], *toml["fallback_models"]], [model, *fallbacks]


def test_the_workflow_and_the_toml_name_the_same_models():
    toml, workflow = chains()
    assert toml == workflow


def test_no_retired_model_and_deepseek_last():
    chain, _ = chains()
    assert not RETIRED & set(chain)
    assert len(set(chain)) == len(chain)
    # deepseek fails with an empty 200, which no fallback behind it would ever see.
    assert chain[-1] == "openai/deepseek-v4-flash"
