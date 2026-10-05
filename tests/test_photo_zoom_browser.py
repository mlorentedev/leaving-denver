"""
The item sheet's photo zoom (FEAT-016): the controls enlarge and fit the photo, a wheel and a
Ctrl+wheel zoom, a double-click and a double-tap toggle about the point that was hit, a pinch
scales by the fingers' spread, a drag pans while enlarged and the pan cannot open a gap, and the
enlarged photo asks for a wider variant. What a swipe and the arrow keys do at fit is already
covered by `test_photo_gallery_browser.py`, which must keep passing unchanged.

The observable is what the browser paints: the computed transform matrix, the `sizes` the image
resolves, `touch-action`, and the photo the strip marks as shown. Harness: browser_harness.py.
"""

import pytest
from browser_harness import needs_chrome, open_page

pytestmark = needs_chrome

CAR = "2019-ford-escape-sel-awd"
FRAME = """
const r = document.getElementById('modalPhotoFrame').getBoundingClientRect();
return [r.left + r.width / 2, r.top + r.height / 2, r.width, r.height];
"""
# The frame's box, for a drag that must stay inside it: the arrows sit at its vertical middle and
# the zoom controls at its bottom left, so a drag runs along a band clear of both.
BOX = """
const r = document.getElementById('modalPhotoFrame').getBoundingClientRect();
return [r.left, r.top, r.right, r.bottom, r.width, r.height];
"""
# What the page paints, plus the point of the photo under a viewport point: enlarging about a
# point is only true if the same bit of the image stays under it.
STATE = """
const img = document.getElementById('modalMainImg');
const frame = document.getElementById('modalPhotoFrame');
const matrix = new DOMMatrix(getComputedStyle(img).transform === 'none' ? '' : getComputedStyle(img).transform);
window.__under = (px, py) => {
  const r = frame.getBoundingClientRect();
  return [(px - (r.left + r.width / 2) - matrix.e) / matrix.a,
          (py - (r.top + r.height / 2) - matrix.f) / matrix.a];
};
const style = getComputedStyle(frame);
// The frame's visible area, padding aside: what the photo must keep covering while it is panned.
const room = [frame.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
              frame.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)];
const strip = [...document.getElementById('modalThumbStrip').children];
return {
  scale: Math.round(matrix.a * 1000) / 1000,
  x: Math.round(matrix.e * 100) / 100,
  y: Math.round(matrix.f * 100) / 100,
  sizes: img.sizes,
  variant: Number((img.currentSrc.match(/-(\\d+)w\\./) || [0, 0])[1]),
  touch: getComputedStyle(frame).touchAction,
  widest: Math.max(...[...img.srcset.matchAll(/(\\d+)w/g)].map(m => Number(m[1]))),
  box: img.clientWidth,
  room: room[0],
  photo: strip.map((t, i) => (t.classList.contains('border-neutral-900') ? i : -1)).filter(i => i >= 0),
  controls: ['modalZoomIn', 'modalZoomOut', 'modalZoomFit'].map(id => {
    const button = document.getElementById(id);
    return button ? button.getAttribute('aria-label') : null;
  }),
};
"""


def open_car(browser, item=CAR):
    """Opens the car's sheet with its photo laid out, and returns a reader of the painted state."""
    browser.run(f"openModal({item!r}); await until(() => sheets().length);")
    browser.run("await until(() => document.getElementById('modalMainImg').clientWidth > 0);")
    read = lambda: browser.run(STATE)  # noqa: E731 — one expression, closing over the page
    read()
    return read


def at_fit(state):
    return state["scale"] == 1 and state["x"] == 0 and state["y"] == 0


def point_under(browser, point):
    """The point of the photo, in its own pixels, that a viewport point shows."""
    return browser.run(f"return window.__under({point[0]}, {point[1]});")


def ceiling(state):
    return min(5, max(2, state["widest"] / state["box"]))


def tap(browser, point):
    """A finger tap, then a wait: a tap's `pointerup` is handled in the renderer after the CDP
    call that sent it returns, so reading the page straight away reads the state before it."""
    browser.swipe(point, point)
    browser.run("await wait(80); return 0;")


@pytest.mark.parametrize(
    ("page", "labels"),
    [
        ("index.html", ["Zoom in", "Zoom out", "Fit"]),
        ("es/index.html", ["Acercar", "Alejar", "Ajustar"]),
    ],
)
def test_the_controls_are_labelled_buttons(tmp_path, page, labels):
    with open_page(tmp_path, page) as browser:
        state = open_car(browser)()
        assert state["controls"] == labels  # in/out/fit, each named in its own language
        assert at_fit(state)


def test_a_button_enlarges_and_fit_returns(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        browser.run("document.getElementById('modalZoomIn').click();")
        assert state()["scale"] > 1
        browser.run("document.getElementById('modalZoomOut').click();")
        assert at_fit(state())  # the first step back out lands on fit, not near it
        browser.run("document.getElementById('modalZoomIn').click();")
        assert state()["scale"] > 1
        browser.run("document.getElementById('modalZoomFit').click();")
        assert at_fit(state())


def test_the_scale_never_leaves_its_range(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        for _ in range(10):
            browser.run("document.getElementById('modalZoomIn').click();")
        top = state()
        # Not merely bounded by the ceiling: it must reach it. An assertion of `<=` passes for a
        # page that always stops at 2, which is exactly the bug pr-agent found on PR #192 (a
        # `Math.max(0, <array>)` that was NaN and silently disabled the dynamic ceiling).
        assert top["scale"] == pytest.approx(ceiling(top), abs=0.01)
        for _ in range(12):
            browser.run("document.getElementById('modalZoomOut').click();")
        assert at_fit(state())  # never below 1, and the shift comes back with it


def test_enlarging_about_a_point_keeps_it_under_the_pointer(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        point = (x + width / 4, y - height / 4)
        before = point_under(browser, point)
        browser.double_click(point)
        assert state()["scale"] > 1
        after = point_under(browser, point)
        assert abs(after[0] - before[0]) < 2 and abs(after[1] - before[1]) < 2


def test_a_pan_cannot_open_a_gap(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        left, top, right, bottom, width, height = browser.run(BOX)
        browser.double_click((left + width / 2, top + height / 2))
        assert state()["scale"] > 1
        # Drag the photo right as far as the frame allows: it must stop at its own edge.
        band = top + 40  # above the arrows, clear of the zoom controls
        browser.drag((left + 20, band), (right - 20, band))
        browser.drag((left + 20, band), (right - 20, band))
        panned = state()
        room = max(0, (panned["box"] * panned["scale"] - panned["room"]) / 2)
        assert room > 0 and 0 < panned["x"] <= room + 1


def test_the_wheel_scrolls_at_fit_and_zooms_when_enlarged(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.wheel((x, y), -240)
        assert at_fit(state())  # at fit the sheet keeps the wheel to itself
        browser.run("document.getElementById('modalZoomIn').click();")
        before = state()["scale"]
        browser.wheel((x, y), -240)
        assert state()["scale"] > before
        browser.wheel((x, y), 240)
        assert state()["scale"] < before + 0.001


def test_ctrl_wheel_enlarges_from_fit_and_leaves_the_page_zoom_alone(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.send(
            "Input.dispatchMouseEvent",
            type="mouseWheel",
            x=x,
            y=y,
            deltaX=0,
            deltaY=-240,
            modifiers=2,  # Ctrl
        )
        assert state()["scale"] > 1
        assert browser.run("return visualViewport ? visualViewport.scale : 1;") == 1


def test_a_double_click_toggles_in_and_out(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.double_click((x - width / 4, y))
        assert state()["scale"] > 1
        browser.double_click((x - width / 4, y))
        assert at_fit(state())


@pytest.mark.parametrize("page", ["index.html", "es/index.html"])
def test_a_double_tap_zooms_on_a_phone(tmp_path, page):
    with open_page(tmp_path, page) as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        point = (x + width / 4, y)
        tap(browser, point)  # one tap: nothing
        assert at_fit(state())
        tap(browser, point)  # the second, close in time and place: zoom
        assert state()["scale"] > 1
        tap(browser, point)
        tap(browser, point)
        assert at_fit(state())


def test_a_pinch_scales_by_the_spread(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        apart = width / 8
        browser.pinch((x, y), apart, apart * 2)
        pinched = state()
        assert 1.5 < pinched["scale"] <= ceiling(pinched)
        browser.pinch((x, y), apart * 2, apart)
        assert state()["scale"] < pinched["scale"]


def test_an_enlarged_photo_pans_instead_of_stepping(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.double_click((x, y))
        before = state()
        assert before["touch"] == "none"  # a finger must pan, so the browser lets go of it
        reach = width / 4
        browser.swipe((x + reach, y), (x - reach, y))  # leftward: the photo follows the finger
        panned = state()
        assert panned["photo"] == before["photo"]  # no step
        assert panned["x"] < before["x"] - 10  # the same drag panned instead
        browser.key("ArrowRight", 39)  # the arrows keep stepping while enlarged
        assert state()["photo"] == [1]


def test_at_fit_the_frame_keeps_its_swipe_and_its_scroll(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        assert state()["touch"] == "pan-y"
        reach = width / 3
        browser.swipe((x + reach, y), (x - reach, y))
        assert state()["photo"] == [1]
        browser.run("document.getElementById('modalZoomFit').click();")
        assert state()["touch"] == "pan-y"


def test_changing_the_photo_resets_the_zoom(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.double_click((x, y))
        assert state()["scale"] > 1
        browser.run("document.getElementById('modalNextPhoto').click();")
        stepped = state()
        assert stepped["photo"] == [1] and at_fit(stepped)
        browser.run("document.getElementById('modalZoomIn').click();")
        browser.key("ArrowLeft", 37)
        assert at_fit(state()) and state()["photo"] == [0]


def test_closing_and_reopening_the_sheet_starts_fitted(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.double_click((x, y))
        assert state()["scale"] > 1
        browser.run(
            "document.querySelector('#itemSheet [data-close-sheet]').click();"
            "await until(() => !sheets().length);"
        )
        assert at_fit(open_car(browser)())


def test_the_enlarged_photo_asks_for_a_wider_variant(tmp_path):
    with open_page(tmp_path, "index.html") as browser:
        state = open_car(browser)
        current = "return document.getElementById('modalMainImg').currentSrc;"
        fitted, fitted_src = state(), browser.run(current)
        assert fitted["widest"] > 0
        browser.run("document.getElementById('modalZoomIn').click();")
        assert state()["sizes"] == "1600px"
        # The frame asks for the widest candidate there is, and the browser fetches it.
        browser.run(
            f"await until(() => document.getElementById('modalMainImg').currentSrc !== {fitted_src!r});"
        )
        assert state()["variant"] > fitted["variant"]
        browser.run("document.getElementById('modalZoomFit').click();")
        assert state()["sizes"] != "1600px"


def test_no_gesture_ever_throws(tmp_path):
    # A listener that throws is where a gesture silently stops working, and the window's own
    # `error` event catches it. Chrome's console also carries a blocked-font message on a staged
    # file:// page (the harness's shape, not the page's), so the collector is the honest signal.
    catcher = (
        "window.__thrown = [];"
        "window.addEventListener('error', e => window.__thrown.push(String(e.message)));"
    )
    with open_page(tmp_path, "index.html", setup=catcher) as browser:
        open_car(browser)
        x, y, width, height = browser.run(FRAME)
        browser.double_click((x + width / 4, y))
        browser.wheel((x, y), -120)
        browser.pinch((x, y), width / 8, width / 4)
        browser.drag((x - width / 4, y), (x + width / 4, y))
        browser.run("document.getElementById('modalZoomFit').click();")
        assert browser.run("return window.__thrown;") == []
