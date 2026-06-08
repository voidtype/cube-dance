"""Inline showcase/index.html into one self-contained file you can send to anyone.

Embeds the compact (web) video variants, the mp3s and the storyboard as base64
data: URIs, so cube-into-2027.html opens offline with a double-click — no assets
folder, no server. Run after rendering the clips / encoding the audio.

    uv run python showcase/build_standalone.py
"""

from __future__ import annotations

import base64
import pathlib

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / "assets"

# token in index.html -> (file to embed, mime). The web video variants keep the
# single file small enough to send; the bundle (index.html) uses the full ones.
EMBED = {
    "assets/moondance.mp4": ("moondance_web.mp4", "video/mp4"),
    "assets/reveal.mp4": ("reveal_web.mp4", "video/mp4"),
    "assets/moondance.mp3": ("moondance.mp3", "audio/mpeg"),
    "assets/smooth.mp3": ("smooth.mp3", "audio/mpeg"),
    "assets/storyboard.jpg": ("storyboard.jpg", "image/jpeg"),
}


def data_uri(path: pathlib.Path, mime: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def main() -> int:
    html = (HERE / "index.html").read_text()
    total = 0
    for token, (fname, mime) in EMBED.items():
        f = ASSETS / fname
        if not f.exists():
            raise SystemExit(f"missing asset: {f}")
        uri = data_uri(f, mime)
        if token not in html:
            raise SystemExit(f"token not found in index.html: {token}")
        html = html.replace(token, uri)
        total += f.stat().st_size
        print(f"  embedded {fname:22s} {f.stat().st_size/1e6:6.2f} MB")
    out = HERE / "cube-into-2027.html"
    out.write_text(html)
    print(f"\n-> {out}  ({out.stat().st_size/1e6:.1f} MB, assets {total/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
