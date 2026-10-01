"""The POSIX Chrome harness must not break collection on Windows."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows-only collection regression")
def test_browser_suite_collects_without_posix_fcntl():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/test_catalog_flows_browser.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(os.name != "posix", reason="the harness reads Chrome over a POSIX pipe")
def test_send_waits_for_an_answer_up_to_its_deadline(tmp_path):
    # A cold Chrome on a fresh CI runner first answered after about 25 s; with the browser's
    # start counted, that ran past the 30 s budget of one command. Only the start waits longer.
    import threading
    import time

    from browser_harness import DEADLINE, STARTUP, Page

    assert STARTUP >= 4 * DEADLINE

    def page_answering_after(seconds):
        to_r, to_w = os.pipe()
        from_r, from_w = os.pipe()

        def answer():
            time.sleep(seconds)
            os.write(from_w, b'{"id": 1, "result": {"targetId": "t"}}\0')

        threading.Thread(target=answer, daemon=True).start()
        return Page(to_w, from_r, tmp_path / "chrome.log")

    with pytest.raises(AssertionError, match="Chrome stopped answering"):
        page_answering_after(1).send("Target.createTarget", deadline=0.2)
    assert page_answering_after(0.3).send("Target.createTarget", deadline=5) == {"targetId": "t"}
