"""Compose the social/link-preview (Open Graph) image for the showcase site.

A gold reveal frame of the cube, darkened, with the event mark — so when the
link is shared it shows a card worth clicking. 1200x630.

    uv run python showcase/make_og.py
"""

from __future__ import annotations

import pathlib
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / "assets"
W, H = 1200, 630


def _font(size, *names):
    for n in names:
        for base in ("/System/Library/Fonts/Supplemental/", "/System/Library/Fonts/"):
            try:
                return ImageFont.truetype(base + n, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main() -> int:
    # pull a gold frame from the reveal clip
    frame = pathlib.Path("/tmp/og_frame.png")
    subprocess.run(["ffmpeg", "-y", "-ss", "22", "-i", str(ASSETS / "reveal.mp4"),
                    "-frames:v", "1", str(frame)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bg = Image.open(frame).convert("RGB")
    # cover-scale to 1200x630
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * s), int(bg.height * s)), Image.LANCZOS)
    x = (bg.width - W) // 2; y = (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H))

    # darken + vignette so the type reads
    ov = Image.new("RGB", (W, H), (0, 0, 0))
    bg = Image.blend(bg, ov, 0.4)
    grad = Image.new("L", (1, H))
    for j in range(H):
        k = j / H
        grad.putpixel((0, j), int(255 * (0.15 + 0.65 * k)))  # darker toward bottom
    mask = grad.resize((W, H))
    bg = Image.composite(ov, bg, mask.point(lambda v: int(v * 0.55)))

    d = ImageDraw.Draw(bg)
    TITLE = "THE WATAGANS"
    _ts = 150
    while _ts > 72:
        f_title = _font(_ts, "Hoefler Text.ttc", "Georgia.ttf", "Times New Roman.ttf")
        if d.textlength(TITLE, font=f_title) <= W - 160:
            break
        _ts -= 4
    f_over = _font(30, "Helvetica.ttc", "Arial.ttf")
    f_sub = _font(34, "Hoefler Text.ttc", "Georgia.ttf")

    def centre(text, font, cy, fill, spacing=0):
        if spacing:
            total = sum(d.textlength(c, font=font) + spacing for c in text) - spacing
            cx = (W - total) / 2
            for c in text:
                d.text((cx, cy), c, font=font, fill=fill)
                cx += d.textlength(c, font=font) + spacing
        else:
            w = d.textlength(text, font=font)
            d.text(((W - w) / 2, cy), text, font=font, fill=fill)

    centre("NEW YEAR’S EVE", f_over, 150, (210, 180, 140), spacing=10)
    # title with a soft shadow
    tw = d.textlength(TITLE, font=f_title)
    d.text(((W - tw) / 2 + 3, 196 + 3), TITLE, font=f_title, fill=(20, 8, 0))
    d.text(((W - tw) / 2, 196), TITLE, font=f_title, fill=(255, 206, 138))
    centre("the Stumpy site · the Watagans", f_sub, 392, (235, 217, 196))

    out = ASSETS / "og-image.jpg"
    bg.save(out, quality=88)
    print(f"-> {out}  ({out.stat().st_size//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
