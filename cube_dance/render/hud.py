"""A minimal on-screen text overlay (HUD) rendered via Pillow into a texture.

Avoids pulling in a UI toolkit for Phase 0 -- Pillow is already a dependency.
Used to show the active navigation mode and the control help so it's clear how
to drive the scene.
"""

from __future__ import annotations

import moderngl as mgl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_HUD_VS = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 uv;
void main() { uv = in_uv; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""
_HUD_FS = """
#version 330
in vec2 uv;
out vec4 f_color;
uniform sampler2D tex;
void main() { f_color = texture(tex, uv); }
"""

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


class HudOverlay:
    def __init__(self, ctx: mgl.Context, font_size: int = 15) -> None:
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=_HUD_VS, fragment_shader=_HUD_FS)
        self.font = _load_font(font_size)
        self._tex: mgl.Texture | None = None
        self._img_w = 0
        self._img_h = 0
        self._vbo = ctx.buffer(reserve=4 * 4 * 4)  # 4 verts * (2 pos + 2 uv) floats
        self.vao = ctx.vertex_array(self.prog, [(self._vbo, "2f 2f", "in_pos", "in_uv")])

    def set_text(self, lines: list[str]) -> None:
        pad = 10
        line_h = (self.font.size + 6) if hasattr(self.font, "size") else 18
        width = 4
        tmp = Image.new("RGBA", (4, 4))
        d = ImageDraw.Draw(tmp)
        for ln in lines:
            box = d.textbbox((0, 0), ln, font=self.font)
            width = max(width, box[2] - box[0])
        img_w = width + pad * 2
        img_h = line_h * len(lines) + pad * 2

        img = Image.new("RGBA", (img_w, img_h), (8, 8, 12, 180))
        draw = ImageDraw.Draw(img)
        for i, ln in enumerate(lines):
            draw.text((pad, pad + i * line_h), ln, font=self.font, fill=(230, 230, 240, 255))
        img = img.transpose(Image.FLIP_TOP_BOTTOM)  # GL texture origin bottom-left

        if self._tex is not None:
            self._tex.release()
        self._tex = self.ctx.texture((img_w, img_h), 4, img.tobytes())
        self._img_w, self._img_h = img_w, img_h

    def render(self, win_w: int, win_h: int, margin: int = 12) -> None:
        if self._tex is None or win_w <= 0 or win_h <= 0:
            return
        # Map a top-left pixel rectangle to NDC.
        x0, y0 = margin, margin
        x1, y1 = margin + self._img_w, margin + self._img_h

        def ndc(px, py):
            return (2.0 * px / win_w - 1.0, 1.0 - 2.0 * py / win_h)

        ax, ay = ndc(x0, y1)  # bottom-left
        bx, by = ndc(x1, y0)  # top-right
        verts = np.array(
            [ax, ay, 0.0, 0.0,  bx, ay, 1.0, 0.0,  ax, by, 0.0, 1.0,  bx, by, 1.0, 1.0],
            dtype="f4",
        )
        self._vbo.write(verts.tobytes())

        ctx = self.ctx
        ctx.disable(mgl.DEPTH_TEST)
        ctx.enable(mgl.BLEND)
        ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        self._tex.use(0)
        try:
            self.prog["tex"].value = 0
        except KeyError:
            pass
        self.vao.render(mgl.TRIANGLE_STRIP, vertices=4)
