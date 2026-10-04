"""
The item sheet's photo gallery in headless Chrome (#168): the arrows, a sideways swipe and the
arrow keys step through the photos and wrap at both ends; the counter and the thumbnail strip
follow; a vertical drag over the photo is a scroll, not a swipe; an item with one photo shows
no arrows. Harness: browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, open_page

pytestmark = needs_chrome

CAR = "2019-ford-escape-sel-awd"
STATE = """
const strip = [...document.getElementById('modalThumbStrip').children];
const item = INVENTORY.items.find(i => i.id === %r);
return {
  shown: document.getElementById('modalMainImg').getAttribute('src'),
  photos: item.photos.map(p => p.src),
  count: document.getElementById('modalPhotoCount').textContent,
  active: strip.map((t, i) => t.classList.contains('border-neutral-900') ? i : -1).filter(i => i >= 0),
  arrows: ['modalPrevPhoto', 'modalNextPhoto'].map(id => !document.getElementById(id).hidden),
};
"""
FRAME = """
const r = document.getElementById('modalPhotoFrame').getBoundingClientRect();
return [r.left + r.width / 2, r.top + r.height / 2, r.width];
"""


def open_car(browser, item=CAR):
    browser.run(f"openModal({item!r}); await until(() => sheets().length);")
    return lambda: browser.run(STATE % item)


def at(state, idx):
    n = len(state["photos"])
    idx %= n
    return (
        state["shown"] == state["photos"][idx]
        and state["count"] == f"{idx + 1} / {n}"
        and state["active"] == [idx]
    )


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_the_arrows_step_and_wrap(tmp_path, page):
    with open_page(tmp_path, page) as browser:
        state = open_car(browser)
        first = state()
        assert len(first["photos"]) > 2 and first["arrows"] == [True, True]
        assert at(first, 0)
        browser.run("document.getElementById('modalNextPhoto').click();")
        assert at(state(), 1)
        browser.run("document.getElementById('modalPrevPhoto').click();")
        browser.run("document.getElementById('modalPrevPhoto').click();")
        assert at(state(), -1)
        browser.run("document.getElementById('modalNextPhoto').click();")
        assert at(state(), 0)


def test_a_real_press_on_an_arrow_steps_once(tmp_path):
    # Pointer handlers sit on the frame around the arrows: a press on one is a click, not a swipe.
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        point = browser.run(
            "const r = document.getElementById('modalNextPhoto').getBoundingClientRect();"
            "return [r.left + r.width / 2, r.top + r.height / 2];"
        )
        browser.drag(tuple(point), tuple(point))
        assert at(state(), 1)
        browser.swipe(tuple(point), tuple(point))
        assert at(state(), 2)


def test_a_mouse_press_released_off_the_photo_leaves_no_swipe_behind(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width = browser.run(FRAME)
        title = browser.run(
            "const r = document.getElementById('modalTitle').getBoundingClientRect();"
            "return [r.left + 5, r.top + r.height / 2];"
        )
        browser.drag((x, y), tuple(title))
        browser.drag((x - width / 3, title[1]), (x + width / 3, y))
        assert at(state(), 0)


def test_the_arrow_keys_step_through_the_photos(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        browser.key("ArrowRight", 39)
        browser.key("ArrowRight", 39)
        assert at(state(), 2)
        browser.key("ArrowLeft", 37)
        assert at(state(), 1)
        assert browser.run("return sheets();") == ["itemSheet"]


def test_a_sideways_swipe_steps_and_a_vertical_drag_does_not(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width = browser.run(FRAME)
        reach = width / 3
        browser.swipe((x + reach, y), (x - reach, y))
        assert at(state(), 1)
        browser.swipe((x - reach, y), (x + reach, y))
        assert at(state(), 0)
        browser.swipe((x - reach, y), (x + reach, y))
        assert at(state(), -1)
        browser.swipe((x, y - 60), (x + 10, y + 60))
        assert at(state(), -1)
        # A tap is not a swipe either.
        browser.swipe((x, y), (x, y))
        assert at(state(), -1)


def test_reopening_starts_at_the_first_photo(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        open_car(browser)
        browser.key("ArrowRight", 39)
        browser.run(
            "document.querySelector('#itemSheet [data-close-sheet]').click();"
            "await until(() => !sheets().length);"
        )
        assert at(open_car(browser)(), 0)


def test_an_item_with_one_photo_shows_no_arrows(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        single = browser.run("return (INVENTORY.items.find(i => i.photos.length === 1) || {}).id;")
        if not single:
            pytest.skip("no item has exactly one photo")
        state = open_car(browser, single)
        assert state()["arrows"] == [False, False]
        browser.key("ArrowRight", 39)
        assert at(state(), 0)
        assert browser.run("return sheets();") == ["itemSheet"]
