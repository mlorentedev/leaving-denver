"""
`make sold` / `pending` / `available` change one line of data/inventory.yaml (#205).

A parse-and-dump round trip drops every comment and re-flows the file (220 changed lines for
two one-word edits). The status commands edit the item's own `status:` line and leave every
other byte alone, so the tests here run them against a copy of the real inventory.
"""

import argparse
from types import SimpleNamespace

import pytest
import yaml

from leaving_denver import cli, site_builder
from leaving_denver.config import INVENTORY_YAML


@pytest.fixture
def real_copy(tmp_path, monkeypatch):
    """A copy of the owner's real inventory, which the commands now edit instead of it."""
    copy = tmp_path / "inventory.yaml"
    copy.write_bytes(INVENTORY_YAML.read_bytes())
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", copy)
    monkeypatch.setattr(cli, "build_all", lambda: None)
    monkeypatch.setattr(cli, "record_sale", lambda *args: None)
    monkeypatch.setattr(cli, "load_private", lambda: {})
    monkeypatch.setattr(cli, "offer_seller_update", lambda: None)
    return copy


def lines_of(path):
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def changed(before, after):
    assert len(before) == len(after)
    return [(a, b) for a, b in zip(before, after, strict=True) if a != b]


def an_item_not(status):
    """(id, status) of a real item whose status is not `status`: the owner's data decides which,
    so no test assumes an item is still Available (lesson-037)."""
    inventory = yaml.safe_load(INVENTORY_YAML.read_text(encoding="utf-8"))
    return next((i["id"], i["status"]) for i in inventory["items"] if i["status"] != status)


def test_the_real_inventory_has_comments_for_the_test_to_protect():
    assert any(line.lstrip().startswith("#") for line in lines_of(INVENTORY_YAML))


@pytest.mark.parametrize(("command", "status"), [("sold", "Sold"), ("pending", "Pending")])
def test_a_status_command_changes_exactly_one_line_of_the_real_inventory(
    real_copy, command, status
):
    item_id, was = an_item_not(status)
    before = lines_of(real_copy)

    getattr(cli, f"cmd_{command}")(SimpleNamespace(id=item_id, price=None))

    after = lines_of(real_copy)
    # Whatever the line's spacing or trailing comment, only the word changes.
    [(old, new)] = changed(before, after)
    assert old.lstrip().startswith(f"status: {was}")
    assert new == old.replace(f"status: {was}", f"status: {status}", 1)
    inventory = yaml.safe_load("".join(after))
    assert next(i for i in inventory["items"] if i["id"] == item_id)["status"] == status
    assert [i["status"] for i in inventory["items"] if i["id"] != item_id] == [
        i["status"] for i in yaml.safe_load("".join(before))["items"] if i["id"] != item_id
    ]


def test_available_undoes_pending_to_the_byte(real_copy):
    original = real_copy.read_bytes()
    item_id, was = an_item_not("Pending")
    if was != "Available":
        site_builder.set_item_status(item_id, "Available")
        original = real_copy.read_bytes()
    cli.cmd_pending(argparse.Namespace(id=item_id))
    assert real_copy.read_bytes() != original
    cli.cmd_available(argparse.Namespace(id=item_id))
    assert real_copy.read_bytes() == original


def test_setting_the_status_it_already_has_leaves_the_file_byte_identical(real_copy):
    before = real_copy.read_bytes()
    item_id, was = an_item_not("")
    site_builder.set_item_status(item_id, was)
    assert real_copy.read_bytes() == before


def test_an_unknown_item_changes_nothing(real_copy, capsys):
    before = real_copy.read_bytes()
    with pytest.raises(SystemExit):
        cli.cmd_pending(argparse.Namespace(id="nope"))
    assert real_copy.read_bytes() == before


def test_a_bundle_with_the_same_id_is_never_the_item(real_copy):
    """`bundles:` entries also start with `- id:`; only `items:` is searched."""
    bundle_id = yaml.safe_load(real_copy.read_text(encoding="utf-8"))["bundles"][0]["id"]
    before = real_copy.read_bytes()
    with pytest.raises(ValueError, match=bundle_id):
        site_builder.set_item_status(bundle_id, "Sold")
    assert real_copy.read_bytes() == before


SMALL = """\
seller:
  status: not an item
items:
# a comment between items
- id: lamp
  title: Lamp
  # keep me
  status: Available  # trailing note
  primary_image: a.jpg
- id: rug
  title: Rug
  primary_image: b.jpg
  specs:
    status: nested
- id: vase
  title: Vase
  size_in: [1, 2]

# after the items
bundles:
- id: lamp
  items: [lamp]
"""


def test_the_line_keeps_its_trailing_comment_and_nothing_else_moves():
    edited = site_builder.edit_item_status(SMALL, "lamp", "Sold")
    assert edited == SMALL.replace("status: Available  # trailing", "status: Sold  # trailing")


def test_an_item_without_a_status_line_gets_one_before_its_photo():
    edited = site_builder.edit_item_status(SMALL, "rug", "Pending")
    assert edited == SMALL.replace(
        "  primary_image: b.jpg\n", "  status: Pending\n  primary_image: b.jpg\n"
    )


def test_an_item_without_status_or_photo_gets_it_after_its_last_field_before_the_blank():
    edited = site_builder.edit_item_status(SMALL, "vase", "Sold")
    assert edited == SMALL.replace("  size_in: [1, 2]\n\n", "  size_in: [1, 2]\n  status: Sold\n\n")


def test_a_nested_status_key_is_not_the_items_status():
    edited = site_builder.edit_item_status(SMALL, "rug", "Sold")
    assert "    status: nested\n" in edited
    assert yaml.safe_load(edited)["items"][1]["specs"] == {"status": "nested"}


def test_crlf_files_keep_their_line_endings():
    crlf = SMALL.replace("\n", "\r\n")
    edited = site_builder.edit_item_status(crlf, "rug", "Sold")
    assert edited == crlf.replace(
        "  primary_image: b.jpg\r\n", "  status: Sold\r\n  primary_image: b.jpg\r\n"
    )
    assert "\n" not in edited.replace("\r\n", "")


def test_an_item_ending_the_file_without_a_newline_still_gets_a_clean_line():
    edited = site_builder.edit_item_status("items:\n- id: a\n  title: A", "a", "Sold")
    assert edited == "items:\n- id: a\n  title: A\n  status: Sold\n"


def test_more_than_one_status_line_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    twice = SMALL.replace("  title: Lamp\n", "  title: Lamp\n  status: Pending\n")
    path = tmp_path / "inventory.yaml"
    path.write_text(twice, encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)
    with pytest.raises(ValueError, match="2 `status:` lines"):
        site_builder.set_item_status("lamp", "Sold")
    assert path.read_text(encoding="utf-8") == twice


def test_the_command_reports_the_refusal_and_exits_without_rebuilding(
    tmp_path, monkeypatch, capsys
):
    twice = SMALL.replace("  title: Lamp\n", "  title: Lamp\n  status: Pending\n")
    path = tmp_path / "inventory.yaml"
    path.write_text(twice, encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: {"items": [{"id": "lamp"}]})
    monkeypatch.setattr(cli, "build_all", lambda: pytest.fail("rebuilt"))
    with pytest.raises(SystemExit) as stop:
        cli.cmd_pending(argparse.Namespace(id="lamp"))
    assert stop.value.code == 1
    out = capsys.readouterr().out
    assert out.startswith("Error:")
    assert "2 `status:` lines" in out
    assert path.read_text(encoding="utf-8") == twice


@pytest.mark.parametrize("line", ["  status: Sold out", '  status: "Sold" extra', "  status:"])
def test_a_status_line_it_cannot_rewrite_in_place_is_refused(line):
    text = SMALL.replace("  status: Available  # trailing note", line)
    with pytest.raises(ValueError, match="cannot rewrite"):
        site_builder.edit_item_status(text, "lamp", "Sold")
