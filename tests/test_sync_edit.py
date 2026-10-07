"""
`leaving-denver sync` edits the photo lines of data/inventory.yaml and nothing else (#219).

The status commands already edit one line (#205). Photo sync still dumped the parsed file, which
drops every comment and re-flows the layout. It now rewrites only the `primary_image:` line and
the `images:` list of the items whose photos changed, and refuses, writing nothing, on a block it
cannot edit safely. The last test is the guard: no source file serializes the inventory.
"""

import ast
import re
from pathlib import Path

import pytest
import yaml

from leaving_denver import cli, image_processor, site_builder
from leaving_denver.config import BASE_DIR, INVENTORY_YAML

SMALL = """\
# owner notes, kept
seller:
  images: not an item
items:
# a comment between items
- id: lamp
  title: Lamp
  # keep me
  photos:
  - lamp-2.jpg
  status: Available  # trailing note
  primary_image: catalog/lamp/lamp-1.jpg
  images:
  - catalog/lamp/lamp-1.jpg
  - catalog/lamp/lamp-2.jpg
  specs:
  - Bright
- id: rug
  title: Rug
  size_in: [1, 2]

# after the items
bundles:
- id: lamp
  items: [lamp]
"""

LAMP_NEW = ["catalog/lamp/lamp-2.jpg", "catalog/lamp/lamp-1.jpg", "catalog/lamp/lamp-3.jpg"]


def edit(text, item_id, images):
    return site_builder.edit_item_photos(text, item_id, images, images[0])


def test_only_the_photo_lines_of_that_item_change():
    edited = edit(SMALL, "lamp", LAMP_NEW)
    assert edited == SMALL.replace(
        "  primary_image: catalog/lamp/lamp-1.jpg\n  images:\n"
        "  - catalog/lamp/lamp-1.jpg\n  - catalog/lamp/lamp-2.jpg\n",
        "  primary_image: catalog/lamp/lamp-2.jpg\n  images:\n"
        "  - catalog/lamp/lamp-2.jpg\n  - catalog/lamp/lamp-1.jpg\n"
        "  - catalog/lamp/lamp-3.jpg\n",
    )
    assert yaml.safe_load(edited)["items"][0]["images"] == LAMP_NEW


def test_photos_that_already_match_leave_the_text_byte_identical():
    same = ["catalog/lamp/lamp-1.jpg", "catalog/lamp/lamp-2.jpg"]
    assert site_builder.edit_item_photos(SMALL, "lamp", same, same[0]) == SMALL


def test_the_primary_line_keeps_its_trailing_comment():
    text = SMALL.replace("lamp-1.jpg\n  images:", "lamp-1.jpg  # the cover\n  images:")
    edited = edit(text, "lamp", LAMP_NEW)
    assert "  primary_image: catalog/lamp/lamp-2.jpg  # the cover\n" in edited


def test_an_item_without_photo_lines_gets_them_after_its_last_field_before_the_blank():
    edited = edit(SMALL, "rug", ["catalog/rug/a.jpg", "catalog/rug/b.jpg"])
    assert edited == SMALL.replace(
        "  size_in: [1, 2]\n\n",
        "  size_in: [1, 2]\n  primary_image: catalog/rug/a.jpg\n  images:\n"
        "  - catalog/rug/a.jpg\n  - catalog/rug/b.jpg\n\n",
    )


def test_an_item_with_only_a_primary_line_gets_the_list_after_it():
    text = SMALL.replace(
        "  size_in: [1, 2]\n", "  primary_image: catalog/rug/a.jpg\n  size_in: [1, 2]\n"
    )
    edited = edit(text, "rug", ["catalog/rug/a.jpg"])
    assert edited == text.replace(
        "  primary_image: catalog/rug/a.jpg\n",
        "  primary_image: catalog/rug/a.jpg\n  images:\n  - catalog/rug/a.jpg\n",
    )


def test_a_name_yaml_would_read_as_something_else_is_quoted():
    edited = edit(SMALL, "rug", ["catalog/rug/#1: a.jpg"])
    assert yaml.safe_load(edited)["items"][1]["images"] == ["catalog/rug/#1: a.jpg"]


def test_crlf_files_keep_their_line_endings():
    crlf = SMALL.replace("\n", "\r\n")
    edited = edit(crlf, "lamp", LAMP_NEW)
    assert "\n" not in edited.replace("\r\n", "")
    assert edited.replace("\r\n", "\n") == edit(SMALL, "lamp", LAMP_NEW)


def test_an_item_ending_the_file_without_a_newline_still_gets_clean_lines():
    edited = edit("items:\n- id: a\n  title: A", "a", ["catalog/a/x.jpg"])
    assert edited == (
        "items:\n- id: a\n  title: A\n  primary_image: catalog/a/x.jpg\n"
        "  images:\n  - catalog/a/x.jpg\n"
    )


def test_a_bare_images_key_ending_the_file_without_a_newline_gets_its_ending_back():
    edited = edit("items:\n- id: a\n  title: A\n  images:", "a", ["catalog/a/x.jpg"])
    assert edited == (
        "items:\n- id: a\n  title: A\n  primary_image: catalog/a/x.jpg\n"
        "  images:\n  - catalog/a/x.jpg\n"
    )


def test_a_file_yaml_cannot_read_after_the_edit_is_a_refusal_not_a_traceback():
    # A tab in the indentation: the edit cannot make this parse, and the error is a ValueError.
    with pytest.raises(ValueError, match="not valid YAML"):
        edit("items:\n- id: a\n\ttitle: A\n", "a", ["catalog/a/x.jpg"])


def test_the_command_refuses_a_file_yaml_cannot_read_without_a_traceback(
    tmp_path, monkeypatch, capsys
):
    broken = "items:\n- id: a\n  title: A\n  images:\n  - x\n  - [unclosed\n"
    path = tmp_path / "inventory.yaml"
    path.write_text(broken, encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)
    monkeypatch.setattr(cli, "load_inventory_yaml", lambda: {"items": [{"id": "a"}]})
    fake_sync(monkeypatch, {"a": ["catalog/a/x.jpg"]})
    with pytest.raises(SystemExit) as stop:
        cli.cmd_sync(None)
    assert stop.value.code == 1
    assert "Error:" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == broken


def test_a_bundle_with_the_same_id_is_never_the_item():
    with pytest.raises(ValueError, match="'nothing'"):
        edit(SMALL, "nothing", LAMP_NEW)


@pytest.mark.parametrize(
    ("old", "new", "why"),
    [
        (
            "  images:\n  - catalog/lamp/lamp-1.jpg\n  - catalog/lamp/lamp-2.jpg\n",
            "  images: [catalog/lamp/lamp-1.jpg, catalog/lamp/lamp-2.jpg]\n",
            "images",
        ),
        ("  primary_image: catalog/lamp/lamp-1.jpg\n", "  primary_image:\n", "primary_image"),
        (
            "  primary_image: catalog/lamp/lamp-1.jpg\n",
            "  primary_image: catalog/lamp/lamp-1.jpg\n  primary_image: x.jpg\n",
            "2 `primary_image:` lines",
        ),
        (
            "  images:\n  - catalog/lamp/lamp-1.jpg\n  - catalog/lamp/lamp-2.jpg\n",
            "  images:\n  - catalog/lamp/lamp-1.jpg\n  # note\n  - catalog/lamp/lamp-2.jpg\n",
            "more than its photos",
        ),
        (
            "  images:\n  - catalog/lamp/lamp-1.jpg\n  - catalog/lamp/lamp-2.jpg\n",
            "  images:\n  - catalog/lamp/lamp-1.jpg\n  - catalog/lamp/lamp-2.jpg\n  images:\n  - x\n",
            "2 `images:` lines",
        ),
    ],
)
def test_a_block_it_cannot_edit_safely_is_refused(old, new, why):
    text = SMALL.replace(old, new)
    assert text != SMALL
    with pytest.raises(ValueError, match=re.escape(why)):
        edit(text, "lamp", LAMP_NEW)


# The command, over a copy of the owner's real inventory.


def lines_of(path):
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


@pytest.fixture
def real_copy(tmp_path, monkeypatch):
    copy = tmp_path / "inventory.yaml"
    copy.write_bytes(INVENTORY_YAML.read_bytes())
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", copy)
    return copy


def fake_sync(monkeypatch, photo_map):
    monkeypatch.setattr(image_processor, "sync_all_photos", lambda: photo_map)


def the_photos_the_owner_has(path):
    """What a sync that found exactly each item's current photos would return."""
    items = yaml.safe_load(path.read_text(encoding="utf-8"))["items"]
    return {i["id"]: list(i["images"]) for i in items if i.get("images")}


def test_the_real_inventory_has_comments_for_the_test_to_protect():
    assert any(line.lstrip().startswith("#") for line in lines_of(INVENTORY_YAML))


def test_a_sync_that_finds_nothing_new_leaves_the_file_byte_identical(real_copy, monkeypatch):
    fake_sync(monkeypatch, the_photos_the_owner_has(real_copy))
    cli.cmd_sync(None)  # once, so the data is in the form sync writes (the owner's may lag)
    settled = real_copy.read_bytes()
    cli.cmd_sync(None)
    assert real_copy.read_bytes() == settled


def test_a_new_photo_changes_only_photo_lines_and_keeps_every_comment(real_copy, monkeypatch):
    photos = the_photos_the_owner_has(real_copy)
    fake_sync(monkeypatch, photos)
    cli.cmd_sync(None)
    before = lines_of(real_copy)
    item_id = next(iter(photos))
    fake_sync(monkeypatch, {**photos, item_id: [*photos[item_id], f"catalog/{item_id}/zz-new.jpg"]})

    cli.cmd_sync(None)

    after = lines_of(real_copy)
    assert [line for line in before if line.lstrip().startswith("#")] == [
        line for line in after if line.lstrip().startswith("#")
    ]
    gone = [line for line in before if line not in after]
    added = [line for line in after if line not in before]
    assert added == [f"  - catalog/{item_id}/zz-new.jpg\n"]
    assert gone == []
    sofa = next(i for i in yaml.safe_load("".join(after))["items"] if i["id"] == item_id)
    assert sofa["images"][-1] == f"catalog/{item_id}/zz-new.jpg"


def test_a_refused_block_writes_nothing_and_exits_with_the_reason(tmp_path, monkeypatch, capsys):
    twice = SMALL.replace("  title: Lamp\n", "  title: Lamp\n  images:\n  - x.jpg\n")
    path = tmp_path / "inventory.yaml"
    path.write_text(twice, encoding="utf-8")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)
    fake_sync(monkeypatch, {"lamp": ["catalog/lamp/lamp-1.jpg", "catalog/lamp/lamp-2.jpg"]})
    with pytest.raises(SystemExit) as stop:
        cli.cmd_sync(None)
    assert stop.value.code == 1
    out = capsys.readouterr().out
    assert "Error:" in out
    assert "2 `images:` lines" in out
    assert path.read_text(encoding="utf-8") == twice


# The guard: nothing may serialize the inventory again.

SOURCES = [*(BASE_DIR / "src").rglob("*.py"), *(BASE_DIR / "scripts").rglob("*.py")]


YAML_WRITERS = {"dump", "safe_dump", "dump_all", "safe_dump_all"}


def serializes_yaml(path: Path) -> list[str]:
    """`yaml.dump`-style calls (also `from yaml import dump`) and any `save_inventory_yaml` name.

    Only the `yaml` module counts: `json.dump` writes other files and is not this guard's."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        hit = ""
        if isinstance(node, ast.Attribute) and node.attr in YAML_WRITERS:
            if isinstance(node.value, ast.Name) and node.value.id == "yaml":
                hit = f"yaml.{node.attr}"
        elif isinstance(node, ast.ImportFrom) and node.module == "yaml":
            hit = next((f"yaml.{a.name}" for a in node.names if a.name in YAML_WRITERS), "")
        elif getattr(node, "id", None) == "save_inventory_yaml" or (
            getattr(node, "attr", None) == "save_inventory_yaml"
            or getattr(node, "name", None) == "save_inventory_yaml"
        ):
            hit = "save_inventory_yaml"
        if hit:
            found.append(f"{path.name}:{node.lineno} {hit}")
    return found


def test_no_command_writes_the_inventory_by_dumping_yaml():
    assert SOURCES, "found no source to scan"
    offenders = [hit for path in SOURCES for hit in serializes_yaml(path)]
    assert offenders == [], f"a YAML dump drops the owner's comments (#205, #219): {offenders}"
    assert not hasattr(site_builder, "save_inventory_yaml")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import yaml\nyaml.dump({}, f)\n", ["bad.py:2 yaml.dump"]),
        ("import yaml\nyaml.safe_dump({}, f)\n", ["bad.py:2 yaml.safe_dump"]),
        ("from yaml import dump\n", ["bad.py:1 yaml.dump"]),
        ("from x import save_inventory_yaml\n", ["bad.py:1 save_inventory_yaml"]),
        ("import json\njson.dump({}, f)\n", []),
        ("from json import dump\ndump({}, f)\n", []),
    ],
)
def test_the_guard_sees_a_yaml_dump_and_not_a_json_one(tmp_path, source, expected):
    sample = tmp_path / "bad.py"
    sample.write_text(source)
    assert serializes_yaml(sample) == expected
