"""
Runs a built catalog page in headless Chrome and drives it over the DevTools protocol
(FEAT-002, TEST-001). Standard library only: Chrome speaks CDP over a pipe on its fds 3 and 4.

The page is staged next to links to the rest of the build (styles, fonts, photos), with an
optional setup <script> before its first script, so stubs
(navigator.share, navigator.clipboard, matchMedia) are in place when the page script reads
them. Once it has loaded, steps run as the body of an async function with these helpers:
wait(ms), until(predicate, ms) which polls until the predicate holds or the time runs out,
and sheets() for the ids of the open sheets. What the steps return comes back as JSON. Keys
and mouse input go through CDP, so the browser treats them as trusted user input.

Real time, not --virtual-time-budget: under virtual time headless Chrome stops producing
frames soon after the first paint, and a <dialog>'s close event waits for a frame
(lesson-017).
Tests using it skip where no Chrome is installed; GitHub's ubuntu runners have one.
"""

import json
import os
import re
import select
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

if os.name == "posix":
    import fcntl

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
CHROME = (
    next(
        (p for p in map(shutil.which, ("google-chrome", "chromium", "chromium-browser")) if p), None
    )
    if os.name == "posix"
    else None
)
needs_chrome = pytest.mark.skipif(CHROME is None, reason="Chrome CDP pipe needs POSIX and Chrome")
DEADLINE = 30
# A cold start on a fresh CI runner outlasted DEADLINE before its first answer (lesson-017).
STARTUP = 120

# Stubs the page's pointer check: True is a desktop mouse, False a phone or a tablet.
POINTER = """
const FINE_POINTER = '(hover: hover) and (pointer: fine)';
const realMatchMedia = window.matchMedia.bind(window);
window.matchMedia = query => query === FINE_POINTER
  ? { matches: %s, media: query, addEventListener() {}, removeEventListener() {} }
  : realMatchMedia(query);
"""

STEPS = """(async () => {
  const wait = ms => new Promise(done => setTimeout(done, ms));
  const until = async (holds, ms = 2000) => {
    for (const end = Date.now() + ms; !holds() && Date.now() < end; ) await wait(20);
  };
  const sheets = () => [...document.querySelectorAll('dialog.sheet[open]')].map(d => d.id);
  %s
})()"""


def pointer(fine):
    return POINTER % ("true" if fine else "false")


def page_items(page):
    """The page's HTML, its og:url and its item ids, in catalog order."""
    html = (PUBLIC / page).read_text(encoding="utf-8")
    og = re.search(r'<meta property="og:url" content="([^"]+)"', html)
    og_url = og and og.group(1)  # the seller page is not shared, so it carries none
    return html, og_url, re.findall(r'data-item="([^"]+)"', html)


def stage(page, html, root, public=PUBLIC):
    """Writes the page under root, with every other file of the build linked around it, so
    its relative links (styles.css, fonts, photos) resolve and the sheets have their layout."""
    source, target = public, root
    for part in Path(page).parts:
        target.mkdir(parents=True, exist_ok=True)
        for entry in source.iterdir():
            if entry.name != part:
                (target / entry.name).symlink_to(entry)
        source, target = source / part, target / part
    target.write_text(html, encoding="utf-8")
    return target


class Page:
    def __init__(self, to_chrome, from_chrome, log):
        self._out, self._in, self._buffer, self._next = to_chrome, from_chrome, b"", 0
        self._events, self._log, self.session = [], log, None
        self.logged = []  # every Log.entryAdded Chrome sent, whoever was waiting for what

    def _read(self, end):
        while b"\0" not in self._buffer:
            ready, _, _ = select.select([self._in], [], [], max(end - time.monotonic(), 0))
            chunk = os.read(self._in, 1 << 16) if ready else b""
            if not chunk:
                log = self._log.read_text(errors="replace")[-2000:] if self._log.exists() else ""
                raise AssertionError(f"Chrome stopped answering: the page never reported\n{log}")
            self._buffer += chunk
        message, self._buffer = self._buffer.split(b"\0", 1)
        message = json.loads(message)
        if message.get("method") == "Log.entryAdded":
            self.logged.append(message["params"]["entry"])
        return message

    def errors(self):
        """The messages of the error-level entries Chrome logged, not counting a failed
        request: a blocked script, an unknown Permissions-Policy feature, an uncaught error."""
        self.run("return 0;")  # a round trip, so whatever Chrome queued has been read
        return [
            e["text"] for e in self.logged if e["level"] == "error" and e["source"] != "network"
        ]

    def send(self, method, deadline=DEADLINE, **params):
        end = time.monotonic() + deadline
        self._next += 1
        message = {"id": self._next, "method": method, "params": params}
        if self.session:
            message["sessionId"] = self.session
        os.write(self._out, json.dumps(message).encode() + b"\0")
        while True:
            reply = self._read(end)
            if reply.get("id") == self._next:
                assert "error" not in reply, f"{method}: {reply['error']}"
                return reply["result"]
            self._events.append(reply)

    def wait_for(self, method):
        end = time.monotonic() + DEADLINE
        while True:
            event = self._events.pop(0) if self._events else self._read(end)
            if event.get("method") == method:
                return event["params"]

    def run(self, steps):
        """Runs steps in the page and returns what they return."""
        result = self.send(
            "Runtime.evaluate",
            expression=STEPS % steps,
            awaitPromise=True,
            returnByValue=True,
        )
        details = result.get("exceptionDetails")
        assert not details, details.get("exception", {}).get("description", details)
        return result["result"].get("value")

    def key(self, key, code):
        for kind in ("rawKeyDown", "keyUp"):
            self.send(
                "Input.dispatchKeyEvent",
                type=kind,
                key=key,
                code=key,
                windowsVirtualKeyCode=code,
                nativeVirtualKeyCode=code,
            )

    def mouse(self, kind, x, y):
        buttons = {"mousePressed": 1, "mouseMoved": 1, "mouseReleased": 0}[kind]
        self.send(
            "Input.dispatchMouseEvent",
            type=kind,
            x=x,
            y=y,
            button="left",
            buttons=buttons,
            clickCount=1,
        )

    def drag(self, start, end):
        """A press at start and a release at end: a plain click when they are one point."""
        self.mouse("mousePressed", *start)
        if start != end:
            self.mouse("mouseMoved", *end)
        self.mouse("mouseReleased", *end)

    def click(self, point, count=1):
        """A real click: press and release at one point. `count` is the click count Chrome
        reads, so a second click with 2 is a double-click and fires `dblclick`."""
        for kind in ("mousePressed", "mouseReleased"):
            self.send(
                "Input.dispatchMouseEvent",
                type=kind,
                x=point[0],
                y=point[1],
                button="left",
                buttons=1 if kind == "mousePressed" else 0,
                clickCount=count,
            )

    def double_click(self, point):
        self.click(point)
        self.click(point, count=2)

    def wheel(self, point, delta_y):
        """A wheel notch at a point. Chrome delivers it on the next round trip, not this one:
        read the page back (`run("return 0;")`, as `errors()` does) before asserting on it."""
        self.send(
            "Input.dispatchMouseEvent",
            type="mouseWheel",
            x=point[0],
            y=point[1],
            deltaX=0,
            deltaY=delta_y,
        )

    def pinch(self, centre, start, end, steps=5):
        """Two fingers either side of centre, moving from `start` to `end` px apart: a real
        pinch, with the second finger put down after the first, as a hand does."""
        x, y = centre

        def fingers(apart):
            return [{"x": x - apart, "y": y}, {"x": x + apart, "y": y}]

        self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=fingers(start)[:1])
        self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=fingers(start))
        for step in range(1, steps + 1):
            apart = start + (end - start) * step / steps
            self.send("Input.dispatchTouchEvent", type="touchMove", touchPoints=fingers(apart))
        self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])

    def swipe(self, start, end, steps=5):
        """A finger put down at start, moved to end in steps, and lifted: a real touch, so the
        page sees touch-action and pointerType 'touch' as on a phone."""
        self.send(
            "Input.dispatchTouchEvent",
            type="touchStart",
            touchPoints=[{"x": start[0], "y": start[1]}],
        )
        for i in range(1, steps + 1):
            point = [a + (b - a) * i / steps for a, b in zip(start, end, strict=True)]
            self.send(
                "Input.dispatchTouchEvent",
                type="touchMove",
                touchPoints=[{"x": point[0], "y": point[1]}],
            )
        self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])


MODULE_SCRIPT = re.compile(r'<script type="module" src="([^"]+)"></script>')


def inline_modules(html, folder):
    """A module script fetched from file:// is blocked as cross-origin, so the staged page
    carries each one inline; nothing in them imports."""
    return MODULE_SCRIPT.sub(
        lambda found: (
            f'<script type="module">{(folder / found.group(1)).read_text("utf-8")}</script>'
        ),
        html,
    )


@contextmanager
def open_page(tmp_path, page, setup="", fragment="", public=PUBLIC, url=None, query=""):
    """Opens a page of `public` (the real build by default; a test may pass a build of its own,
    such as one sealed with a fixture envelope).

    With `url` the page is fetched from there instead (a test serving a build over HTTP, for
    what only a response header can show, such as a Content-Security-Policy); `setup` then runs
    on the new document before its own scripts. `query` is appended to a staged page's address,
    before the fragment (a landing from a tracked link, `utm_source=flyer`)."""
    staged = None
    if url is None:
        html = inline_modules((public / page).read_text(encoding="utf-8"), (public / page).parent)
        # Before the first script of any kind: a page may open with data blocks, not code. A
        # page with no script of its own (the flyer) takes the setup at the end of its head.
        first = re.search(r"<script[ >]", html)
        first_script = first.start() if first else html.index("</head>")
        staged = stage(
            page,
            html[:first_script] + f"<script>{setup}</script>\n" + html[first_script:],
            tmp_path / "site",
            public,
        )
    # Every end is moved above fd 4 first, so the dup2 calls below never meet themselves: a
    # dup2 onto its own fd keeps close-on-exec and Chrome would start without its pipe.
    ends = []
    for fd in (*os.pipe(), *os.pipe()):
        ends.append(fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 5))
        os.close(fd)
    to_chrome_r, to_chrome_w, from_chrome_r, from_chrome_w = ends
    log = tmp_path / "chrome.log"

    def wire():  # in the child: CDP in on fd 3, out on fd 4
        os.dup2(to_chrome_r, 3)
        os.dup2(from_chrome_w, 4)

    with log.open("wb") as errors:
        chrome = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--remote-debugging-pipe",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={tmp_path / 'profile'}",
                "about:blank",
            ],
            preexec_fn=wire,
            close_fds=False,
            stdout=subprocess.DEVNULL,
            stderr=errors,
        )
    os.close(to_chrome_r)
    os.close(from_chrome_w)
    browser = Page(to_chrome_w, from_chrome_r, log)
    try:
        # The first answer waits for Chrome to start, which a fresh runner makes slow.
        target = browser.send("Target.createTarget", deadline=STARTUP, url="about:blank")[
            "targetId"
        ]
        attached = browser.send("Target.attachToTarget", targetId=target, flatten=True)
        browser.session = attached["sessionId"]
        browser.send("Page.enable")
        browser.send("Log.enable")
        target_url = url or staged.as_uri()
        if url is not None and setup:
            browser.send("Page.addScriptToEvaluateOnNewDocument", source=setup)
        browser.send(
            "Page.navigate",
            url=target_url + (f"?{query}" if query else "") + (f"#{fragment}" if fragment else ""),
        )
        browser.wait_for("Page.loadEventFired")
        # The load event carries no frame: make sure it was the page, not about:blank.
        scheme = "http:" if url is not None else "file:"
        assert (
            browser.run(
                f"await until(() => location.protocol === '{scheme}' && document.readyState === 'complete');"
                "return location.protocol;"
            )
            == scheme
        )
        yield browser
    finally:
        chrome.kill()
        chrome.wait(timeout=DEADLINE)
        os.close(to_chrome_w)
        os.close(from_chrome_r)


def run_page(tmp_path, page, steps, setup="", fragment="", public=PUBLIC, url=None, query=""):
    with open_page(tmp_path, page, setup, fragment, public, url, query) as browser:
        return browser.run(steps)
