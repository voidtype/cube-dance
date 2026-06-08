#!/usr/bin/env python3
"""Local dev server for the browser cube preview (pure additive — engine untouched).

- Docroot = the repo root, so the app (/web/), the test audio
  (/showcase/assets/smooth.mp3) and the engine zip are all reachable.
- Dynamic route GET /cube_dance.zip -> zips the LIVE cube_dance/ package in memory
  (always current, no on-disk copy) so Pyodide can import the real engine.
- Correct MIME for .mjs/.wasm/.mp3/.py/.json. No COOP/COEP (single-threaded
  Pyodide needs no SharedArrayBuffer; that would only break CDN imports).

    uv run python web/serve.py            # -> http://localhost:8137/web/
"""

from __future__ import annotations

import argparse
import io
import os
import zipfile
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
PKG_DIR = os.path.join(REPO_ROOT, "cube_dance")
ZIP_ROUTE = "/cube_dance.zip"
ZIP_ARCNAME = "cube_dance"

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", ".mypy_cache",
                ".pytest_cache", ".ruff_cache", ".idea", ".vscode", "node_modules"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".map": "application/json; charset=utf-8",
    ".py": "text/x-python; charset=utf-8", ".wasm": "application/wasm",
    ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".aiff": "audio/aiff",
    ".m4a": "audio/mp4", ".flac": "audio/flac", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".zip": "application/zip",
}


def build_zip_bytes(pkg_dir: str, arcname_root: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(pkg_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for name in filenames:
                if name.endswith(EXCLUDE_SUFFIXES):
                    continue
                abs_path = os.path.join(dirpath, name)
                if not os.path.isfile(abs_path):
                    continue
                arcname = os.path.join(arcname_root, os.path.relpath(abs_path, pkg_dir))
                zf.write(abs_path, arcname)
    return buf.getvalue()


class Handler(SimpleHTTPRequestHandler):
    extensions_map = dict(MIME)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def _is_zip(self) -> bool:
        # match /cube_dance.zip at any base (e.g. /web/cube_dance.zip) so the app
        # can fetch it with a relative path (works the same when hosted online).
        return self.path.split("?", 1)[0].endswith("/cube_dance.zip")

    def do_GET(self) -> None:
        if self._is_zip():
            return self._zip(False)
        return super().do_GET()

    def do_HEAD(self) -> None:
        if self._is_zip():
            return self._zip(True)
        return super().do_HEAD()

    def _zip(self, head_only: bool) -> None:
        try:
            data = build_zip_bytes(PKG_DIR, ZIP_ARCNAME)
        except OSError as exc:
            return self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def log_message(self, fmt, *args):  # quieter logs
        if "/cube_dance.zip" in (self.path or "") or self.path in ("/web/", "/web/index.html"):
            super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8137)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    handler = partial(Handler, directory=REPO_ROOT)
    httpd = ThreadingHTTPServer((a.bind, a.port), handler)
    url = f"http://localhost:{a.port}/web/"
    print(f"\n  Cube Dance — browser preview")
    print(f"  serving repo root: {REPO_ROOT}")
    print(f"  engine zip:        http://localhost:{a.port}{ZIP_ROUTE}  (live cube_dance/)")
    print(f"\n  ▶  open  {url}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
