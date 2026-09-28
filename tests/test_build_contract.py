"""
Build contract: the builder fails closed, and unpublished items never reach build/public/.
"""

import json

import pytest
import yaml

from leaving_denver import site_builder

PHONE = "+15555550100"


def inventory(*, hidden_published=False):
    item = {
        "category": "Living Room",
        "brand": "Test",
        "recommended_list_price": 10,
        "original_price": 20,
        "dimensions": "1 x 1",
        "specs": ["a", "b"],
    }
    return {
        "seller": {"location": "DTC, CO 80111"},
        "items": [
            {**item, "id": "shown-lamp", "title": "Shown lamp"},
            {
                **item,
                "id": "hidden-widget",
                "title": "Hidden widget",
                "published": hidden_published,
            },
        ],
        "bundles": [
            {
                "id": "bundle-with-hidden",
                "name": "With hidden",
                "items": ["shown-lamp", "hidden-widget"],
            },
            {"id": "bundle-shown-only", "name": "Shown only", "items": ["shown-lamp"]},
        ],
    }


@pytest.fixture
def public_dir(tmp_path, monkeypatch):
    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    return dist


def text_under(root):
    """Every file path and file body under root, as one string."""
    parts = []
    for path in sorted(root.rglob("*")):
        parts.append(str(path.relative_to(root)))
        if path.is_file() and path.suffix in {".html", ".txt", ".json", ""}:
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


@pytest.mark.parametrize(
    ("script", "missing"),
    [
        ("const INVENTORY = {items: []};\nconst _C = {{ contact_json | safe }};", "inventory_json"),
        ("const INVENTORY = {{ inventory_json | safe }};\nconst _C = {};", "contact_json"),
    ],
)
def test_missing_marker_fails(public_dir, tmp_path, monkeypatch, script, missing):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "index.html").write_text(f"<script>{script}</script>")
    monkeypatch.setattr(site_builder, "TEMPLATES_DIR", templates)
    with pytest.raises(RuntimeError, match=missing):
        site_builder.build_public_site(inventory())


def test_unpublished_item_and_its_bundles_are_absent_from_public(public_dir):
    # A photo left over from an earlier build, when the item was still published.
    stale = public_dir / "catalog" / "hidden-widget" / "old.jpg"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"jpeg")

    site_builder.build_public_site(inventory())

    public = text_under(public_dir)
    assert "shown-lamp" in public
    assert "bundle-shown-only" in public
    assert "hidden-widget" not in public
    assert "bundle-with-hidden" not in public


def test_published_defaults_to_true(public_dir):
    site_builder.build_public_site(inventory(hidden_published=True))
    assert "hidden-widget" in text_under(public_dir)


def test_unpublished_item_is_in_private_marked_draft(tmp_path, monkeypatch):
    private_dir = tmp_path / "private"
    monkeypatch.setenv("SELLER_PHONE", PHONE)
    monkeypatch.setattr(site_builder, "load_private", lambda: {"floors": {}})
    monkeypatch.setattr(site_builder, "DIST_PRIVATE_DIR", private_dir)
    monkeypatch.setattr(site_builder, "INVENTORY_JSON_PRIVATE", tmp_path / "inventory.json")
    monkeypatch.setattr(site_builder, "PRIVATE_POSTER_HTML", private_dir / "poster_assistant.html")

    site_builder.build_private_workspace(inventory())

    data = json.loads((private_dir / "inventory.json").read_text())
    drafts = {i["id"]: i.get("draft", False) for i in data["items"]}
    assert drafts == {"shown-lamp": False, "hidden-widget": True}
    assert "item.draft" in (private_dir / "poster_assistant.html").read_text()


def test_publish_flag_survives_yaml_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "inventory.yaml"
    path.write_text(yaml.dump(inventory(), sort_keys=False))
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", path)

    site_builder.save_inventory_yaml(site_builder.load_inventory_yaml())

    hidden = yaml.safe_load(path.read_text())["items"][1]
    assert hidden["published"] is False


def test_bundle_items_must_be_a_list(public_dir):
    data = inventory()
    data["bundles"][0]["items"] = "shown-lamp and hidden-widget"
    with pytest.raises(RuntimeError, match="bundle-with-hidden"):
        site_builder.build_public_site(data)


def test_undefined_field_fails_the_build(tmp_path, monkeypatch):
    from jinja2 import UndefinedError

    (tmp_path / "card.html").write_text("<h2>{{ item.titel }}</h2>")
    monkeypatch.setattr(site_builder, "TEMPLATES_DIR", tmp_path)
    with pytest.raises(UndefinedError, match="titel"):
        site_builder.render("card.html", item={"title": "Lamp"})


CAR = {
    "id": "2019-ford-escape-sel-awd",
    "category": "Vehicle",
    "title": "2019 Ford Escape SEL AWD",
    "recommended_list_price": 11875,
}


@pytest.mark.parametrize("published", [True, False])
def test_vehicle_card_follows_the_publish_flag(public_dir, published):
    data = inventory()
    data["items"].append({**CAR, "published": published})

    site_builder.build_public_site(data)

    page = (public_dir / "index.html").read_text(encoding="utf-8")
    assert ("2019-ford-escape" in text_under(public_dir)) is published
    assert ("Vehicle" in page.split("<script>")[0]) is published
