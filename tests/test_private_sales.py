"""
Realized sale prices are private (BUG-008): the repo is public, so `sold <id> <price>` records
the price in data/private.sops.yaml, never in data/inventory.yaml.
"""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from leaving_denver import cli, private_data

ROOT = Path(__file__).resolve().parents[1]


def test_public_inventory_holds_no_realized_prices():
    data = yaml.safe_load((ROOT / "data" / "inventory.yaml").read_text(encoding="utf-8"))
    assert not [i["id"] for i in data["items"] if "realized_price" in i]


@pytest.fixture(autouse=True)
def no_real_private_file(monkeypatch):
    """`sold` reads the tracking to list take-downs: never from the owner's real file."""
    monkeypatch.setattr(cli, "load_private", lambda: {})


def fake_inventory():
    return {"items": [{"id": "lamp", "title": "Lamp", "status": "Available"}], "bundles": []}


def test_sold_with_a_price_records_it_privately(monkeypatch):
    inv, saved, recorded = fake_inventory(), [], []
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inv)
    monkeypatch.setattr(cli, "save_inventory_yaml", saved.append)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(
        cli, "record_sale", lambda item_id, price, on: recorded.append((item_id, price, on))
    )
    cli.cmd_sold(SimpleNamespace(id="lamp", price=120))
    assert recorded == [("lamp", 120, date.today())]
    assert saved[-1]["items"][0]["status"] == "Sold"
    assert "realized_price" not in saved[-1]["items"][0]


def test_sold_fails_before_touching_anything_if_the_price_cannot_be_kept(monkeypatch):
    monkeypatch.setattr(cli, "load_inventory_yaml", fake_inventory)
    monkeypatch.setattr(cli, "save_inventory_yaml", lambda d: pytest.fail("saved"))

    def refuse(item_id, price, on):
        raise RuntimeError("sops unavailable")

    monkeypatch.setattr(cli, "record_sale", refuse)
    with pytest.raises(SystemExit):
        cli.cmd_sold(SimpleNamespace(id="lamp", price=120))


def test_sold_on_an_unknown_id_records_no_price(monkeypatch):
    monkeypatch.setattr(cli, "load_inventory_yaml", fake_inventory)
    monkeypatch.setattr(cli, "record_sale", lambda *a: pytest.fail("recorded"))
    with pytest.raises(SystemExit):
        cli.cmd_sold(SimpleNamespace(id="typo", price=120))


def test_record_sale_sets_one_key_with_sops(monkeypatch, tmp_path):
    monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", tmp_path / "private.sops.yaml")
    calls = []
    monkeypatch.setattr(private_data.shutil, "which", lambda _: "/usr/bin/sops")
    monkeypatch.setattr(
        private_data.subprocess,
        "run",
        lambda args, **kw: (
            calls.append((args, kw["input"])) or SimpleNamespace(returncode=0, stderr="")
        ),
    )
    private_data.record_sale("lamp", 120, date(2026, 10, 7))
    path = str(private_data.PRIVATE_SOPS_YAML)
    # The sale travels on stdin: nothing in argv reveals it.
    assert calls == [
        (
            ["sops", "set", "--value-stdin", path, '["sales"]["lamp"]'],
            '{"price": 120, "at": "2026-10-07"}',
        )
    ]


def test_record_sale_raises_when_sops_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(private_data, "PRIVATE_SOPS_YAML", tmp_path / "private.sops.yaml")
    monkeypatch.setattr(private_data.shutil, "which", lambda _: "/usr/bin/sops")
    monkeypatch.setattr(
        private_data.subprocess,
        "run",
        lambda args, **kw: SimpleNamespace(returncode=1, stderr="no key"),
    )
    with pytest.raises(RuntimeError, match="no key"):
        private_data.record_sale("lamp", 120, date(2026, 10, 7))
