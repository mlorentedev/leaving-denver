"""
A build reads data/inventory.yaml and writes only build output (BUG-006).
"""

import yaml

from leaving_denver import site_builder

INVENTORY = {
    "seller": {"location": "DTC, CO 80111"},
    "items": [
        {
            "id": "shown-lamp",
            "category": "Living Room",
            "title": "Shown lamp",
            "recommended_list_price": 10,
            "images": ["catalog/shown-lamp/old.jpg"],
        }
    ],
    "bundles": [],
}


def test_build_does_not_rewrite_the_inventory_yaml(tmp_path, monkeypatch):
    source = tmp_path / "inventory.yaml"
    # Hand-written formatting that a yaml.dump round trip would change.
    source.write_text("# owner notes\n" + yaml.dump(INVENTORY, sort_keys=True, width=40))
    before = source.read_bytes()

    dist = tmp_path / "public"
    monkeypatch.setenv("SELLER_PHONE", "+15555550100")
    monkeypatch.setattr(site_builder, "INVENTORY_YAML", source)
    monkeypatch.setattr(site_builder, "DIST_DIR", dist)
    monkeypatch.setattr(site_builder, "PUBLIC_INDEX_HTML", dist / "index.html")
    monkeypatch.setattr(site_builder, "PUBLIC_ROBOTS_TXT", dist / "robots.txt")
    monkeypatch.setattr(site_builder, "PUBLIC_HEADERS", dist / "_headers")
    monkeypatch.setattr(site_builder, "load_private", lambda: {})
    monkeypatch.setattr(
        site_builder, "sync_all_photos", lambda: {"shown-lamp": ["catalog/shown-lamp/new.jpg"]}
    )

    site_builder.build_all()

    assert source.read_bytes() == before
    # The synced photos still reach the page, from memory.
    assert "catalog/shown-lamp/new.jpg" in (dist / "index.html").read_text()
