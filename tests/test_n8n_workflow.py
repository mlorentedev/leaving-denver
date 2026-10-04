"""The Craigslist bump reminder (integrations/n8n): the message is typed into the workflow, so
nothing in it may be a fact that lives in the data and goes stale (an item name, a price)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "integrations/n8n/workflows/craigslist_48h_bump_reminder.json"


def reminder_text():
    nodes = json.loads(WORKFLOW.read_text(encoding="utf-8"))["nodes"]
    return next(n for n in nodes if n["type"] == "n8n-nodes-base.telegram")["parameters"]["text"]


def test_the_reminder_names_no_price_and_no_item():
    text = reminder_text()
    assert not re.search(r"\$\s?\d", text), "a price typed into the reminder goes stale"
    inventory = (ROOT / "data/inventory.yaml").read_text(encoding="utf-8")
    titles = re.findall(r"^  title: (.+)$", inventory, re.M)
    assert titles, "no item title found: the pattern is stale"
    for title in titles:
        assert title.strip("'\"") not in text, title


def test_the_reminder_does_not_tell_the_seller_to_renew_the_car():
    """A paid cars-by-owner post cannot be renewed (seller-playbook.md)."""
    text = reminder_text()
    assert "Escape" not in text
    assert "cannot be renewed" in text
