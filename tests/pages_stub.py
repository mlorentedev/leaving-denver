"""How Cloudflare Pages answers a path it has no file for, and what its `_headers` file adds, for the
stub servers of the smoke and policy tests."""

import re
from pathlib import Path


class MissingPath:
    """Mix in before `SimpleHTTPRequestHandler`. With a top-level 404.html Pages answers a missing
    path with a 404 and that file's body, at the requested URL. Without one it runs the site as a
    single-page app: the home page and a 200 (BUG-013)."""

    spa_fallback = False
    not_found_page = "404.html"

    def send_error(self, code, message=None, explain=None):
        page = Path(self.directory) / ("index.html" if self.spa_fallback else self.not_found_page)
        if code != 404 or not page.is_file():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(200 if self.spa_fallback else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def parse_headers_file(text):
    """A Pages `_headers` file as [(pattern, [(name, value)])]. A `! Name` line (detach) has
    the value None."""
    rules = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            rules.append((line.strip(), []))
        elif line.strip().startswith("!"):
            rules[-1][1].append((line.strip()[1:].strip(), None))
        else:
            name, _, value = line.strip().partition(":")
            rules[-1][1].append((name.strip(), value.strip()))
    return rules


def pages_headers_for(text, path):
    """What Pages adds to a static response at `path`: every matching rule applies, a header
    named twice is joined with a comma, and a detached header is gone. Splats only."""
    path = path.split("?")[0]
    added, detached = {}, set()
    for pattern, headers in parse_headers_file(text):
        if not re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), path):
            continue
        for name, value in headers:
            if value is None:
                detached.add(name.lower())
                continue
            key = next((key for key in added if key.lower() == name.lower()), name)
            added[key] = f"{added[key]}, {value}" if key in added else value
    return {name: value for name, value in added.items() if name.lower() not in detached}


def policy_directives(policy):
    """A Content-Security-Policy as {directive: [sources]}."""
    parsed = {}
    for part in filter(str.strip, policy.split(";")):
        name, *sources = part.split()
        parsed[name.lower()] = sources
    return parsed


class AppliesHeadersFile:
    """Mix in before `SimpleHTTPRequestHandler`: each response carries what the build's own
    `_headers` file says Pages would add at the requested path."""

    headers_file = ""

    def added_headers(self):
        return pages_headers_for(self.headers_file, self.path)

    def end_headers(self):
        for name, value in self.added_headers().items():
            self.send_header(name, value)
        super().end_headers()
