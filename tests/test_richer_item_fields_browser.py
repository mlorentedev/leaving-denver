"""
The item sheet's new rows in headless Chrome (FEAT-007): the badges and the known-flaws list
come from the item's data, flaws go in as text, and an item with none shows no flaws section.
Harness: browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

SHEET = """
const read = id => {
  openModal(id);
  const rows = sel => [...document.querySelectorAll(sel)].map(el => el.textContent.trim());
  return {
    badges: rows('#modalBadges [data-role]'),
    flaws: [...document.querySelectorAll('#modalFlaws li')].map(li => li.lastChild.textContent),
    flawsHidden: document.getElementById('modalFlawsBox').hidden,
    markup: document.getElementById('modalFlaws').querySelectorAll('b, img, script').length,
  };
};
const sofa = INVENTORY.items.find(i => i.id === 'sofa-sleeper');
const clean = read(sofa.id);
const real = { discount: sofa.discount_pct, sizes: sofa.size_badges };
sofa.flaws = ['Scuff <b>on</b> the arm', 'Zipper sticks'];
const flawed = read(sofa.id);
return { clean, flawed, real, free: INVENTORY.items.find(i => i.free).id,
  freeBadges: read(INVENTORY.items.find(i => i.free).id).badges };
"""


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_the_sheet_shows_badges_and_flaws_from_the_data(tmp_path, page):
    result = run_page(tmp_path, page, SHEET)
    clean, flawed = result["clean"], result["flawed"]
    # Discount first, then each size badge, as the data holds them.
    assert len(clean["badges"]) == 1 + len(result["real"]["sizes"])
    assert clean["badges"][0].startswith(f"{result['real']['discount']}%")
    assert clean["badges"][1:] == result["real"]["sizes"]
    assert clean["flawsHidden"] is True and clean["flaws"] == []
    assert flawed["flawsHidden"] is False
    assert flawed["flaws"] == ["Scuff <b>on</b> the arm", "Zipper sticks"]
    assert flawed["markup"] == 0
    assert result["freeBadges"] == []
