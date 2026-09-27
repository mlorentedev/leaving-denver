"""
An item's cover photo is chosen by its `cover:` field, not by filename order (BUG-002).
"""

import pytest

from leaving_denver.site_builder import apply_photos

SYNCED = ["catalog/sofa/a_dimensions.jpg", "catalog/sofa/b_front.jpg", "catalog/sofa/c_open.jpg"]


def test_cover_goes_first():
    item = {"id": "sofa", "cover": "b_front.jpg"}
    apply_photos(item, SYNCED)
    assert item["images"] == [
        "catalog/sofa/b_front.jpg",
        "catalog/sofa/a_dimensions.jpg",
        "catalog/sofa/c_open.jpg",
    ]
    assert item["primary_image"] == "catalog/sofa/b_front.jpg"


def test_without_cover_the_order_is_kept():
    item = {"id": "sofa"}
    apply_photos(item, SYNCED)
    assert item["images"] == SYNCED


def test_unknown_cover_fails_the_build():
    with pytest.raises(RuntimeError, match="sofa.*missing.jpg"):
        apply_photos({"id": "sofa", "cover": "missing.jpg"}, SYNCED)
