from leaving_denver.site_builder import load_inventory_yaml, sanitize_public_inventory


def test_dinnerware_is_private_without_hiding_take_everything():
    inventory = load_inventory_yaml()
    dinnerware = next(
        item for item in inventory["items"] if item["id"] == "dinnerware-glassware-set"
    )
    assert dinnerware["published"] is False
    assert all(
        "dinnerware-glassware-set" not in bundle.get("items", []) for bundle in inventory["bundles"]
    )

    public = sanitize_public_inventory(inventory)
    assert "dinnerware-glassware-set" not in {item["id"] for item in public["items"]}
    assert "bundle-kitchen-island" not in {bundle["id"] for bundle in public["bundles"]}
    assert any(bundle["everything"] for bundle in public["bundles"])
