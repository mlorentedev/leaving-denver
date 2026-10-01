"""
The item sheet in headless Chrome (FEAT-011): every spec and included line becomes a bullet,
the summary joins condition, dimensions and colour, and opening another item replaces the
bullets rather than adding to them. Harness: browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, run_page

pytestmark = needs_chrome

CAR = "2019-ford-escape-sel-awd"
SHEET = """
const shown = id => {
  openModal(id);
  const item = INVENTORY.items.find(i => i.id === id);
  const texts = sel => [...document.querySelectorAll(sel)].map(li => li.lastChild.textContent);
  return {
    facts: texts('#itemFacts li'), specs: item.specs,
    included: texts('#modalIncluded li'), expectedIncluded: item.included,
    includedHidden: document.getElementById('modalIncludedBox').hidden,
    summary: document.getElementById('modalSummary').textContent,
    expectedSummary: [item.condition, item.dimensions, item.color].filter(Boolean).join(' · '),
  };
};
const car = shown(%r);
const other = shown(INVENTORY.items.find(i => i.id !== %r && i.specs.length).id);
return { car, other };
"""


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_the_sheet_shows_the_whole_item(tmp_path, page):
    result = run_page(tmp_path, page, SHEET % (CAR, CAR))
    for shown in result.values():
        assert shown["facts"] == shown["specs"]
        assert shown["included"] == shown["expectedIncluded"]
        assert shown["includedHidden"] == (not shown["expectedIncluded"])
        assert shown["summary"] == shown["expectedSummary"]
    assert len(result["car"]["facts"]) > 4
