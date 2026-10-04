"""
The item sheet's button names what the buyer wants (#170): an item says "I want it" and its
text asks for a pickup time; the car, which nobody buys from a button, says "I'm interested"
and asks to see it. Opening one after the other relabels the same button. Harness:
browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

CAR = "2019-ford-escape-sel-awd"
CTA = """
const shown = id => {
  openModal(id);
  const link = document.getElementById('modalSmsLink');
  const item = INVENTORY.items.find(i => i.id === id);
  return { label: link.textContent.trim(), body: decodeURIComponent(link.href.split(SMS_BODY)[1]),
           title: item.short_title };
};
const item = INVENTORY.items.find(i => i.category !== 'Vehicle' && i.status !== 'Sold').id;
return { item: shown(item), car: shown(%r), again: shown(item) };
"""
COPY = {
    "index.html": {
        "item": ("I want it — text me", "Hi! I want the", "When could I pick it up?"),
        "car": ("I'm interested — text me", "Hi! I'm interested in the", "When could I see it?"),
    },
    "es/index.html": {
        "item": (
            "Lo quiero — escríbeme",
            "¡Hola! Quiero comprar",
            "¿Cuándo podría pasar a recoger?",
        ),
        "car": ("Me interesa — escríbeme", "¡Hola! Me interesa el", "¿Cuándo podría verlo?"),
    },
}


@pytest.mark.parametrize("page", COPY)
def test_the_button_and_text_say_what_the_buyer_wants(tmp_path, page):
    result = run_page(tmp_path, page, CTA % CAR)
    assert result["again"] == result["item"]
    for kind in ("item", "car"):
        label, opening, ask = COPY[page][kind]
        shown = result[kind]
        assert shown["label"] == label
        assert shown["body"].startswith(f"{opening} {shown['title']} (")
        assert shown["body"].endswith(ask)
