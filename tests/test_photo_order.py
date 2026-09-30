"""
An item's photo order comes from its `photos:` list, not from file names (BUG-002, FEAT-012).
The first photo is the cover, and so the link preview. Own photos go first and stock photos
last; which photo leads is the owner's call, recorded in the data.
"""

import pytest
import yaml

from leaving_denver.config import DATA_DIR
from leaving_denver.site_builder import apply_photos

SYNCED = ["catalog/sofa/a_dimensions.jpg", "catalog/sofa/b_front.jpg", "catalog/sofa/c_open.jpg"]


def test_listed_photos_go_first_in_their_order():
    item = {"id": "sofa", "photos": ["c_open.jpg", "b_front.jpg"]}
    apply_photos(item, SYNCED)
    assert item["images"] == [
        "catalog/sofa/c_open.jpg",
        "catalog/sofa/b_front.jpg",
        "catalog/sofa/a_dimensions.jpg",
    ]
    assert item["primary_image"] == "catalog/sofa/c_open.jpg"


def test_names_are_matched_the_way_photo_sync_renames_them():
    item = {"id": "sofa", "photos": ["B Front.HEIC"]}
    apply_photos(item, SYNCED)
    assert item["images"][0] == "catalog/sofa/b_front.jpg"


def test_without_a_list_the_name_order_is_kept():
    item = {"id": "sofa"}
    apply_photos(item, SYNCED)
    assert item["images"] == SYNCED


def test_an_unknown_photo_fails_the_build():
    with pytest.raises(RuntimeError, match="sofa.*missing.jpg"):
        apply_photos({"id": "sofa", "photos": ["b_front.jpg", "missing.jpg"]}, SYNCED)


def test_a_photo_listed_twice_fails_the_build():
    with pytest.raises(RuntimeError, match="sofa.*b_front.jpg.*twice"):
        apply_photos({"id": "sofa", "photos": ["b_front.jpg", "b_front.jpg"]}, SYNCED)


def test_cover_is_no_longer_read():
    # `photos:` replaced it; a leftover `cover:` would be silently ignored, so it fails instead.
    with pytest.raises(RuntimeError, match="sofa.*cover.*photos"):
        apply_photos({"id": "sofa", "cover": "b_front.jpg"}, SYNCED)


def test_every_item_with_several_photos_lists_them_all():
    items = yaml.safe_load((DATA_DIR / "inventory.yaml").read_text(encoding="utf-8"))["items"]
    photos_dir = DATA_DIR.parent / "content" / "photos"
    for item in items:
        folder = photos_dir / item["id"]
        own = sorted(p.stem.lower() for p in folder.iterdir()) if folder.is_dir() else []
        if len(own) > 1:
            listed = sorted(name.rsplit(".", 1)[0].lower() for name in item.get("photos", []))
            assert listed == own, f"{item['id']}: photos: must list every photo in order"
