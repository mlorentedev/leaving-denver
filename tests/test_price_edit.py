"""
`make reprice` changes the asking price in data/inventory.yaml itself (#236).

It used to record the price privately and print "Edit its price in the inventory too": ten drops
on 2026-10-13 meant ten hand edits, and one slip leaves the site and the price log disagreeing.
Like the status commands (#205), it edits the item's one `recommended_list_price:` line and
leaves every other byte alone, so these tests run it against a copy of the real inventory.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
import yaml

from leaving_denver import cli, site_builder
from leaving_denver.config import INVENTORY_YAML


@pytest.fixture
def real_copy(tmp_path, monkeypatch):
    """A copy of the owner's real inventory, which the command edits instead of it."""
    copy = tmp_path / "inventory.yaml"
    copy.write_bytes(INVENTORY_YAML.read_bytes())
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", copy)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(cli, "offer_seller_update", lambda: None)
    recorded = []
    monkeypatch.setattr(cli, "record_price", lambda *args: recorded.append(args))
    return SimpleNamespace(path=copy, recorded=recorded)


def lines_of(path):
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def a_priced_item():
    """(id, price) of a real item with a price, chosen from the owner's data (lesson-037)."""
    inventory = yaml.safe_load(INVENTORY_YAML.read_text(encoding="utf-8"))
    return next(
        (i["id"], i["recommended_list_price"])
        for i in inventory["items"]
        if i.get("recommended_list_price", 0) > 1
    )


def reprice(item_id, price, on=None):
    cli.cmd_reprice(SimpleNamespace(id=item_id, price=price, on=on))


def test_reprice_changes_exactly_the_price_line_of_the_real_inventory(real_copy):
    item_id, was = a_priced_item()
    before = lines_of(real_copy.path)

    reprice(item_id, was - 1)

    after = lines_of(real_copy.path)
    diff = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(diff) == 1
    assert diff[0][1].startswith(f"  recommended_list_price: {was - 1}")
    item = next(i for i in yaml.safe_load("".join(after))["items"] if i["id"] == item_id)
    assert item["recommended_list_price"] == was - 1
    assert real_copy.recorded == [(item_id, was - 1, date.today())]


def test_a_backdated_reprice_still_sets_todays_price(real_copy):
    item_id, was = a_priced_item()
    yesterday = date.today() - timedelta(days=1)
    reprice(item_id, was - 1, on=yesterday.isoformat())
    assert f"  recommended_list_price: {was - 1}\n" in lines_of(real_copy.path)
    assert real_copy.recorded == [(item_id, was - 1, yesterday)]


def test_a_reprice_dated_after_today_is_refused_and_nothing_changes(real_copy, capsys):
    item_id, was = a_priced_item()
    before = real_copy.path.read_bytes()
    with pytest.raises(SystemExit):
        reprice(item_id, was - 1, on=(date.today() + timedelta(days=1)).isoformat())
    assert capsys.readouterr().out.startswith("Error:")
    assert real_copy.path.read_bytes() == before
    assert real_copy.recorded == []


SMALL = """\
seller:
  name: Owner
items:
- id: rug
  title: Rug
  recommended_list_price: 40   # paid 120
  status: Available
- id: lamp
  title: Lamp
  recommended_list_price: 20
  status: Available
"""


def test_the_comment_on_the_price_line_survives():
    edited = site_builder.edit_item_price(SMALL, "rug", 30)
    assert "  recommended_list_price: 30   # paid 120\n" in edited
    assert edited.replace("30   #", "40   #") == SMALL


def test_windows_line_endings_are_kept():
    crlf = SMALL.replace("\n", "\r\n")
    edited = site_builder.edit_item_price(crlf, "lamp", 15)
    assert edited == crlf.replace("price: 20\r\n", "price: 15\r\n")


def test_the_same_price_changes_no_byte():
    assert site_builder.edit_item_price(SMALL, "lamp", 20) == SMALL


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (SMALL.replace("  recommended_list_price: 40   # paid 120\n", ""), "has no"),
        (
            SMALL.replace(
                "  status: Available\n- id: lamp",
                "  recommended_list_price: 41\n  status: Available\n- id: lamp",
                1,
            ),
            "has 2",
        ),
        (SMALL.replace("price: 40 ", "price: '40'"), "cannot rewrite"),
        (SMALL.replace("price: 40 ", "price: 39.5"), "cannot rewrite"),
    ],
    ids=["missing", "twice", "quoted", "cents"],
)
def test_a_price_line_it_cannot_rewrite_is_refused(text, reason):
    with pytest.raises(ValueError, match=reason):
        site_builder.edit_item_price(text, "rug", 30)


def test_a_refused_edit_records_nothing_and_writes_nothing(real_copy, capsys):
    item_id, was = a_priced_item()
    text = real_copy.path.read_text(encoding="utf-8")
    start, _ = site_builder.item_block(text.splitlines(keepends=True), item_id)
    lines = text.splitlines(keepends=True)
    at = next(
        n for n in range(start, len(lines)) if lines[n].startswith("  recommended_list_price:")
    )
    lines[at] = f"  recommended_list_price: '{was}'\n"
    real_copy.path.write_text("".join(lines), encoding="utf-8")
    before = real_copy.path.read_bytes()

    with pytest.raises(SystemExit):
        reprice(item_id, was - 1)

    out = capsys.readouterr().out
    assert out.startswith("Error:") and "Nothing changed." in out
    assert real_copy.path.read_bytes() == before
    assert real_copy.recorded == [], "a refused edit must not leave a price in the log (#220)"


def test_the_message_no_longer_asks_for_a_hand_edit(real_copy, capsys):
    item_id, was = a_priced_item()
    reprice(item_id, was - 1)
    assert "Edit its price" not in capsys.readouterr().out
