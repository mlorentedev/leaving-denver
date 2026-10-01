import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/leaving_denver"
# I sell alone: the owner's voice is first person singular, in English and in Spanish.
PLURAL = re.compile(r"\b(?:we|our|we'll|nosotros|nuestr[oa]s?|podemos)\b", re.IGNORECASE)


def test_seller_copy_uses_first_person_singular():
    template = (SOURCE / "templates/poster_assistant.html").read_text(encoding="utf-8")
    assert not re.search(r"\b(?:we|our|we'll)\b", template, re.IGNORECASE)


def test_the_seller_tool_uses_first_person_singular():
    for path in ("assets/seller.mjs", "templates/seller.html"):
        text = (SOURCE / path).read_text(encoding="utf-8")
        assert not PLURAL.search(text), f"{path}: {PLURAL.search(text).group(0)}"
