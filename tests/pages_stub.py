"""How Cloudflare Pages answers a path it has no file for, for the smoke tests' stub servers."""

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
