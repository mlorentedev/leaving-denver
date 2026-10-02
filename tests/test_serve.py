"""
Local preview server: loopback-only by default, and no path escapes its build roots.
"""

import http.client
import threading

import pytest

from leaving_denver.cli import make_server, resolve_request_path
from leaving_denver.config import DIST_DIR


@pytest.mark.parametrize(
    "path",
    [
        "/catalog/../../../pyproject.toml",
        "/private/../../pyproject.toml",
        "/catalog/%2e%2e/%2e%2e/%2e%2e/pyproject.toml",
        "/../data/private.sops.yaml",
        "/data/inventory.json",
    ],
)
def test_paths_outside_the_build_roots_are_refused(path):
    resolved = resolve_request_path(path)
    assert resolved is None or resolved.is_relative_to(DIST_DIR)
    assert resolved is None or not resolved.exists()


def test_routes():
    assert resolve_request_path("/") == DIST_DIR
    assert resolve_request_path("/robots.txt?x=1") == DIST_DIR / "robots.txt"
    # The old private workspace is gone (ADR-007): its paths are plain public paths now.
    assert (
        resolve_request_path("/private/inventory.json") == DIST_DIR / "private" / "inventory.json"
    )
    assert resolve_request_path("/poster_assistant.html") == DIST_DIR / "poster_assistant.html"


def test_server_binds_loopback_and_refuses_traversal_over_http():
    server = make_server(port=0)
    host, port = server.server_address[:2]
    assert host == "127.0.0.1"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # http.client sends the path verbatim; curl would collapse the `..`.
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/catalog/../../../pyproject.toml")
        resp = conn.getresponse()
        body = resp.read()
        assert resp.status == 404
        assert b"[project]" not in body
    finally:
        server.shutdown()
        server.server_close()
