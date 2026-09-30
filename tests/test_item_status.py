"""
Items are Available, Pending (reserved, awaiting pickup) or Sold, and the page says which
(FEAT-006). Sold items sort last; a bundle is on sale only while all its items are.
"""

import argparse
from types import SimpleNamespace

import pytest

from leaving_denver import cli, site_builder


def data(**statuses):
    items = [
        {"id": i, "category": "Living Room", "title": i, "recommended_list_price": 10, "status": s}
        for i, s in statuses.items()
    ]
    return {
        "items": items,
        "bundles": [
            {"id": "ab", "name": "AB", "items": ["a", "b"], "bundle_price": 15},
            {"id": "cd", "name": "CD", "items": ["c", "d"], "bundle_price": 15},
        ],
    }


def test_unknown_status_fails_the_build():
    with pytest.raises(RuntimeError, match="b.*Reserved"):
        site_builder.sanitize_public_inventory(
            data(a="Available", b="Reserved", c="Sold", d="Sold")
        )


def test_status_defaults_to_available():
    inv = data(a="Available", b="Available", c="Available", d="Available")
    del inv["items"][0]["status"]
    public = site_builder.sanitize_public_inventory(inv)
    assert public["items"][0]["status"] == "Available"


def test_sold_items_sort_last_and_the_rest_keep_their_order():
    public = site_builder.sanitize_public_inventory(
        data(a="Sold", b="Available", c="Pending", d="Available")
    )
    assert [i["id"] for i in public["items"]] == ["b", "c", "d", "a"]


@pytest.mark.parametrize("taken", ["Pending", "Sold"])
def test_bundle_with_a_taken_item_is_unavailable(taken):
    public = site_builder.sanitize_public_inventory(
        data(a="Available", b=taken, c="Available", d="Available")
    )
    availability = {b["id"]: b["available"] for b in public["bundles"]}
    assert availability == {"ab": False, "cd": True}


def test_realized_price_stays_private():
    inv = data(a="Sold", b="Available", c="Available", d="Available")
    inv["items"][0]["realized_price"] = 7
    public = site_builder.sanitize_public_inventory(inv)
    assert "realized_price" not in public["items"][-1]
    assert "7" not in repr(public["items"][-1].values())


def test_status_label_is_localized_and_the_key_kept():
    inv = data(a="Pending", b="Available", c="Available", d="Available")
    public = site_builder.sanitize_public_inventory(inv)
    for locale in ("en", "es"):
        translations = site_builder.load_locale(locale)
        localized = site_builder.localize_public_inventory(public, inv, locale, translations, "")
        item = localized["items"][0]
        assert item["status"] == "Pending"
        assert item["status_label"] == translations["statuses"]["Pending"]


@pytest.mark.parametrize(
    ("command", "status"), [("pending", "Pending"), ("available", "Available"), ("sold", "Sold")]
)
def test_status_commands_set_the_status_and_rebuild(monkeypatch, command, status):
    inv = data(a="Available", b="Pending", c="Available", d="Available")
    saved, built = [], []
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: inv)
    monkeypatch.setattr(cli, "save_inventory_yaml", saved.append)
    monkeypatch.setattr(cli, "build_all", lambda: built.append(True))
    getattr(cli, f"cmd_{command}")(SimpleNamespace(id="b", price=None))
    assert saved[0]["items"][1]["status"] == status
    assert built


def test_status_commands_reject_an_unknown_id(monkeypatch):
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: data(a="Available", b="", c="", d=""))
    monkeypatch.setattr(cli, "save_inventory_yaml", lambda d: pytest.fail("saved"))
    with pytest.raises(SystemExit):
        cli.cmd_pending(argparse.Namespace(id="nope", price=None))
