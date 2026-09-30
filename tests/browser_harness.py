"""
Runs a built catalog page in headless Chrome and drives it over the DevTools protocol
(FEAT-002, TEST-001). Standard library only: Chrome speaks CDP over a pipe on its fds 3 and 4.

The page is staged with an optional setup <script> before its first script, so stubs
(navigator.share, navigator.clipboard, matchMedia) are in place when the page script reads
them. Once it has loaded, steps run as the body of an async function with these helpers:
wait(ms), until(predicate, ms) which polls until the predicate holds or the time runs out,
and sheets() for the ids of the open sheets. What the steps return comes back as JSON. Keys
and mouse input go through CDP, so the browser treats them as trusted user input.

Real time, not --virtual-time-budget: under virtual time headless Chrome stops producing
frames after the first paint, and a <dialog>'s close event waits for a frame (lesson-017).
Tests using it skip where no Chrome is installed; GitHub's ubuntu runners have one.
"""

import json
import os
import re
import select
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "build" / "public"
CHROME = next(
    (p for p in map(shutil.which, ("google-chrome", "chromium", "chromium-browser")) if p), None
)
needs_chrome = pytest.mark.skipif(CHROME is None, reason="no Chrome to run the page in")
DEADLINE = 30

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
    og_url = re.search(r'<meta property="og:url" content="([^"]+)"', html).group(1)
    return html, og_url, re.findall(r'data-item="([^"]+)"', html)


class Page:
    def __init__(self, to_chrome, from_chrome):
        self._out, self._in, self._buffer, self._next = to_chrome, from_chrome, b"", 0
        self._events, self.session = [], None

    def _read(self):
        while b"\0" not in self._buffer:
            ready, _, _ = select.select([self._in], [], [], DEADLINE)
            chunk = os.read(self._in, 1 << 16) if ready else b""
            assert chunk, "Chrome stopped answering: the page never reported"
            self._buffer += chunk
        message, self._buffer = self._buffer.split(b"\0", 1)
        return json.loads(message)

    def send(self, method, **params):
        self._next += 1
        message = {"id": self._next, "method": method, "params": params}
        if self.session:
            message["sessionId"] = self.session
        os.write(self._out, json.dumps(message).encode() + b"\0")
        while True:
            reply = self._read()
            if reply.get("id") == self._next:
                assert "error" not in reply, f"{method}: {reply['error']}"
                return reply["result"]
            self._events.append(reply)

    def wait_for(self, method):
        while True:
            event = self._events.pop(0) if self._events else self._read()
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


@contextmanager
def open_page(tmp_path, page, setup="", fragment=""):
    html, _, _ = page_items(page)
    first_script = html.index("<script>")
    staged = tmp_path / "site" / page
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text(
        html[:first_script] + f"<script>{setup}</script>\n" + html[first_script:],
        encoding="utf-8",
    )
    to_chrome_r, to_chrome_w = os.pipe()
    from_chrome_r, from_chrome_w = os.pipe()

    def wire():  # in the child: CDP in on fd 3, out on fd 4
        os.dup2(to_chrome_r, 3)
        os.dup2(from_chrome_w, 4)

    chrome = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--remote-debugging-pipe",
            f"--user-data-dir={tmp_path / 'profile'}",
            "about:blank",
        ],
        preexec_fn=wire,
        close_fds=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.close(to_chrome_r)
    os.close(from_chrome_w)
    browser = Page(to_chrome_w, from_chrome_r)
    try:
        target = browser.send("Target.createTarget", url="about:blank")["targetId"]
        attached = browser.send("Target.attachToTarget", targetId=target, flatten=True)
        browser.session = attached["sessionId"]
        browser.send("Page.enable")
        browser.send("Page.navigate", url=staged.as_uri() + (f"#{fragment}" if fragment else ""))
        browser.wait_for("Page.loadEventFired")
        yield browser
    finally:
        chrome.kill()
        chrome.wait(timeout=DEADLINE)
        os.close(to_chrome_w)
        os.close(from_chrome_r)


def run_page(tmp_path, page, steps, setup="", fragment=""):
    with open_page(tmp_path, page, setup, fragment) as browser:
        return browser.run(steps)
