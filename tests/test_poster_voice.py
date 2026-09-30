import re
from pathlib import Path


def test_seller_copy_uses_first_person_singular():
    template = (
        Path(__file__).resolve().parents[1] / "src/leaving_denver/templates/poster_assistant.html"
    ).read_text(encoding="utf-8")
    assert not re.search(r"\b(?:we|our|we'll)\b", template, re.IGNORECASE)
