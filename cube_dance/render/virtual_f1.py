"""On-screen virtual Traktor Kontrol F1 panel.

Drawn with Pillow into a texture (redraw-on-change) and shown as an overlay in
the right quarter. Knobs and faders are click-drag widgets, buttons are grey and
light when toggled, a 7-segment display shows P, the browse encoder changes P on
scroll, and the 4x4 pads are shown. Interaction writes a shared ControlState.
"""

from __future__ import annotations

import moderngl as mgl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..control.mapping import FADER_ROLES, KNOB_ROLES
from ..control.state import ControlState

PANEL_W, PANEL_H = 360, 880

_VS = """
#version 330
in vec2 in_pos; in vec2 in_uv; out vec2 uv;
void main(){ uv = in_uv; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""
_FS = """
#version 330
in vec2 uv; out vec4 f; uniform sampler2D tex;
void main(){ f = texture(tex, uv); }
"""

_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]

# 7-segment digit -> active segments (a,b,c,d,e,f,g).
_SEG = {
    0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc",
    5: "afgcd", 6: "afgecd", 7: "abc", 8: "abcdefg", 9: "abcdfg",
}

# Lit colours for the function buttons (grey when off).
_BTN_COLOR = {
    "SYNC": (240, 120, 20), "QUANT": (240, 120, 20), "CAPTURE": (240, 120, 20),
    "SHIFT": (220, 220, 225), "REVERSE": (240, 120, 20), "TYPE": (240, 120, 20),
    "SIZE": (240, 120, 20), "BROWSE": (40, 90, 230),
}
_PAD_PALETTE = [  # 4 rows x 4 cols, roughly the F1 default
    (210, 40, 40), (220, 110, 30), (220, 150, 30), (210, 200, 40),
    (150, 200, 40), (60, 180, 60), (40, 180, 110), (40, 190, 180),
    (40, 150, 210), (50, 90, 210), (90, 60, 210), (140, 50, 200),
    (180, 40, 180), (210, 40, 140), (210, 40, 90), (210, 60, 60),
]


def _font(size: int):
    for p in _FONTS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


class VirtualF1:
    def __init__(self, ctx: mgl.Context) -> None:
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=_VS, fragment_shader=_FS)
        self._vbo = ctx.buffer(reserve=4 * 4 * 4)
        self.vao = ctx.vertex_array(self.prog, [(self._vbo, "2f 2f", "in_pos", "in_uv")])
        self._tex: mgl.Texture | None = None
        self._dirty = True
        self._rect = (0.0, 0.0, 0.0, 0.0)  # screen px: x0, y0, w, h
        self._scale = 1.0
        self._drag = None  # (kind, index, start_val, start_iy)
        self._font = _font(15)
        self._small = _font(11)
        self._layout()

    # --- Layout (panel-image pixels) ----------------------------------------
    def _layout(self) -> None:
        cxs = [54, 142, 230, 318]
        self.knobs = [(cx, 118, 34) for cx in cxs]  # (cx, cy, r)
        self.faders = [(cx, 180, 344, 12) for cx in cxs]  # (cx, top, bottom, half-width)
        self.buttons = {
            "SYNC": (14, 372, 98, 408), "QUANT": (104, 372, 188, 408), "CAPTURE": (194, 372, 278, 408),
            "SHIFT": (10, 420, 70, 456), "REVERSE": (76, 420, 138, 456), "TYPE": (144, 420, 206, 456),
            "SIZE": (212, 420, 274, 456), "BROWSE": (280, 420, 346, 456),
        }
        self.display = (282, 364, 324, 406)
        self.encoder = (343, 385, 14)  # cx, cy, r -- beside the display, above BROWSE
        self.pads_rect = (16, 474, 344, 812)  # x0,y0,x1,y1 (4x4)
        self.stop_rect = (16, 822, 344, 858)

    # --- Screen placement ----------------------------------------------------
    def set_screen(self, win_w: int, win_h: int) -> None:
        w = float(min(max(win_w * 0.26, 300), 460))
        self._scale = w / PANEL_W
        h = PANEL_H * self._scale
        margin = 16.0
        x0 = win_w - w - margin
        y0 = max(8.0, (win_h - h) * 0.5)
        self._rect = (x0, y0, w, h)

    def contains(self, sx: float, sy: float) -> bool:
        x0, y0, w, h = self._rect
        return x0 <= sx <= x0 + w and y0 <= sy <= y0 + h

    def _to_img(self, sx: float, sy: float) -> tuple[float, float]:
        x0, y0, _, _ = self._rect
        return (sx - x0) / self._scale, (sy - y0) / self._scale

    # --- Interaction ---------------------------------------------------------
    def on_press(self, sx: float, sy: float, state: ControlState) -> bool:
        ix, iy = self._to_img(sx, sy)
        for i, (cx, cy, r) in enumerate(self.knobs):
            if abs(ix - cx) <= r and abs(iy - cy) <= r:
                self._drag = ("knob", i, state.knobs[i], iy)
                return True
        for i, (cx, top, bot, hw) in enumerate(self.faders):
            if abs(ix - cx) <= hw + 10 and top - 12 <= iy <= bot + 12:
                state.faders[i] = float(np.clip((bot - iy) / (bot - top), 0.0, 1.0))
                state.focus_deck = i  # touching a fader focuses that deck
                self._drag = ("fader", i, state.faders[i], iy)
                self._dirty = True
                return True
        for name, (x0, y0, x1, y1) in self.buttons.items():
            if x0 <= ix <= x1 and y0 <= iy <= y1:
                state.toggle(name)
                self._dirty = True
                return True
        px0, py0, px1, py1 = self.pads_rect
        if px0 <= ix <= px1 and py0 <= iy <= py1:
            c = min(3, max(0, int((ix - px0) / ((px1 - px0) / 4))))  # column = deck
            r = min(3, max(0, int((iy - py0) / ((py1 - py0) / 4))))  # row = trigger
            state.press_pad(c, r)  # app fires this deck's trigger (quantised if QUANT)
            self._dirty = True
            return True
        sx0, sy0, sx1, sy1 = self.stop_rect  # bottom row = channel select
        if sx0 <= ix <= sx1 and sy0 <= iy <= sy1:
            col = min(3, max(0, int((ix - sx0) / ((sx1 - sx0) / 4))))
            state.focus_deck = col
            self._dirty = True
            return True
        return True  # swallow clicks anywhere on the panel

    def on_drag(self, sx: float, sy: float, state: ControlState) -> bool:
        if self._drag is None:
            return self.contains(sx, sy)
        kind, i, start_val, start_iy = self._drag
        _, iy = self._to_img(sx, sy)
        if kind == "knob":
            state.knobs[i] = float(np.clip(start_val - (iy - start_iy) / 150.0, 0.0, 1.0))
        elif kind == "fader":
            cx, top, bot, hw = self.faders[i]
            state.faders[i] = float(np.clip((bot - iy) / (bot - top), 0.0, 1.0))
        self._dirty = True
        return True

    def on_release(self) -> None:
        self._drag = None

    def on_scroll(self, sx: float, sy: float, direction: int, state: ControlState) -> bool:
        ix, iy = self._to_img(sx, sy)
        ecx, ecy, er = self.encoder
        if abs(ix - ecx) <= er + 14 and abs(iy - ecy) <= er + 14:
            state.step_encoder(1 if direction > 0 else -1)
            self._dirty = True
            return True
        return self.contains(sx, sy)

    def mark_dirty(self) -> None:
        self._dirty = True

    # --- Rendering -----------------------------------------------------------
    def _draw_7seg(self, d: ImageDraw.ImageDraw, x, y, w, h, digit, color):
        t = max(2, int(w * 0.20))
        midy = y + h / 2
        segs = {
            "a": (x + t, y, x + w - t, y + t),
            "f": (x, y + t, x + t, midy),
            "b": (x + w - t, y + t, x + w, midy),
            "g": (x + t, midy - t / 2, x + w - t, midy + t / 2),
            "e": (x, midy, x + t, y + h - t),
            "c": (x + w - t, midy, x + w, y + h - t),
            "d": (x + t, y + h - t, x + w - t, y + h),
        }
        on = _SEG.get(int(digit) % 10, "")
        for name, box in segs.items():
            d.rectangle(box, fill=color if name in on else (40, 22, 6))

    def _image(self, state: ControlState, deck_labels=None, focus: int = 0,
               knob_labels=None, pad_colors=None) -> Image.Image:
        img = Image.new("RGBA", (PANEL_W, PANEL_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, PANEL_W - 1, PANEL_H - 1), radius=14, fill=(22, 22, 26, 238),
                            outline=(70, 70, 78, 255), width=2)
        d.text((14, 8), "TRAKTOR  F1", font=self._font, fill=(235, 235, 240, 255))

        for i, (cx, cy, r) in enumerate(self.knobs):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(48, 48, 54), outline=(90, 90, 98), width=2)
            d.ellipse((cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6), fill=(34, 34, 40))
            ang = (state.knobs[i] - 0.5) * 2.0 * (2.30)  # +-130 deg
            ex = cx + (r - 6) * np.sin(ang)
            ey = cy - (r - 6) * np.cos(ang)
            d.line((cx, cy, ex, ey), fill=(230, 180, 60), width=3)
            label = (knob_labels[i] if knob_labels and i < len(knob_labels) else KNOB_ROLES[i])
            d.text((cx - 18, cy + r + 2), str(label)[:9], font=self._small, fill=(170, 170, 178))

        for i, (cx, top, bot, hw) in enumerate(self.faders):
            focused = i == focus
            # Focused deck gets a highlighted track + caps.
            track = (90, 80, 40) if focused else (40, 40, 46)
            d.rounded_rectangle((cx - 3, top, cx + 3, bot), radius=3, fill=track)
            hy = bot - state.faders[i] * (bot - top)
            cap = (230, 180, 60) if focused else (140, 140, 150)
            d.rounded_rectangle((cx - hw, hy - 9, cx + hw, hy + 9), radius=4,
                                fill=(80, 76, 60) if focused else (70, 70, 78), outline=cap, width=2 if focused else 1)
            label = (deck_labels[i] if deck_labels and i < len(deck_labels) else FADER_ROLES[i])
            d.text((cx - 20, bot + 4), f"{i + 1} {label}"[:10], font=self._small,
                   fill=(235, 205, 110) if focused else (120, 120, 130))

        for name, (x0, y0, x1, y1) in self.buttons.items():
            on = state.buttons.get(name, False)
            fill = _BTN_COLOR[name] if on else (58, 58, 64)
            txt = (20, 20, 24) if on and name == "SHIFT" else (235, 235, 240)
            d.rounded_rectangle((x0, y0, x1, y1), radius=5, fill=fill, outline=(95, 95, 104), width=1)
            tb = d.textbbox((0, 0), name, font=self._small)
            d.text(((x0 + x1 - (tb[2] - tb[0])) / 2, (y0 + y1 - (tb[3] - tb[1])) / 2 - 2),
                   name, font=self._small, fill=txt)

        # Display (2-digit 7-seg) + encoder.
        dx0, dy0, dx1, dy1 = self.display
        d.rounded_rectangle((dx0 - 4, dy0 - 4, dx1 + 4, dy1 + 4), radius=4, fill=(10, 6, 4))
        dw = (dx1 - dx0 - 6) / 2
        self._draw_7seg(d, dx0, dy0, dw, dy1 - dy0, state.p // 10, (255, 130, 20))
        self._draw_7seg(d, dx0 + dw + 6, dy0, dw, dy1 - dy0, state.p % 10, (255, 130, 20))
        ecx, ecy, er = self.encoder
        d.ellipse((ecx - er, ecy - er, ecx + er, ecy + er), fill=(50, 50, 56), outline=(95, 95, 104), width=2)
        d.line((ecx, ecy, ecx, ecy - er + 4), fill=(150, 150, 158), width=2)
        d.text((ecx - er - 4, ecy + er + 2), "PRESET", font=self._small, fill=(120, 120, 130))

        # Pads 4x4: column = deck, row = that deck's preset trigger (its colour).
        px0, py0, px1, py1 = self.pads_rect
        cw, ch = (px1 - px0) / 4, (py1 - py0) / 4
        for c_ in range(4):  # column = deck/channel
            for r_ in range(4):  # row = trigger
                idx = r_ * 4 + c_
                x, y = px0 + c_ * cw, py0 + r_ * ch
                base = None
                if pad_colors is not None and c_ < len(pad_colors) and r_ < len(pad_colors[c_]):
                    base = pad_colors[c_][r_]
                if base is None:  # no trigger on this cell
                    d.rounded_rectangle((x + 4, y + 4, x + cw - 4, y + ch - 4), radius=6, fill=(28, 28, 32))
                    continue
                glow = max(0.0, min(1.0, state.pad_glow[idx]))
                s = 0.40 + 0.60 * glow
                col = tuple(int(min(255, ch_ * s)) for ch_ in base)
                outline = (235, 205, 110) if c_ == focus else (70, 70, 78)
                d.rounded_rectangle((x + 4, y + 4, x + cw - 4, y + ch - 4), radius=6,
                                    fill=col, outline=outline, width=2 if c_ == focus else 1)
        # STOP row = channel select; the selected channel lights brightest.
        sx0, sy0, sx1, sy1 = self.stop_rect
        sw = (sx1 - sx0) / 4
        for c_ in range(4):
            on = c_ == focus
            d.rounded_rectangle((sx0 + c_ * sw + 3, sy0, sx0 + (c_ + 1) * sw - 3, sy1), radius=4,
                                fill=(235, 150, 40) if on else (120, 64, 20),
                                outline=(245, 220, 150) if on else (90, 50, 16), width=2 if on else 1)
        return img

    def render(self, win_w: int, win_h: int, state: ControlState,
               deck_labels=None, focus: int = 0, knob_labels=None, pad_colors=None) -> None:
        self.set_screen(win_w, win_h)
        if self._tex is None or self._dirty:
            img = self._image(state, deck_labels, focus, knob_labels, pad_colors).transpose(Image.FLIP_TOP_BOTTOM)
            if self._tex is not None:
                self._tex.release()
            self._tex = self.ctx.texture((PANEL_W, PANEL_H), 4, img.tobytes())
            self._dirty = False

        x0, y0, w, h = self._rect

        def ndc(px, py):
            return (2.0 * px / win_w - 1.0, 1.0 - 2.0 * py / win_h)

        ax, ay = ndc(x0, y0 + h)
        bx, by = ndc(x0 + w, y0)
        verts = np.array([ax, ay, 0, 0, bx, ay, 1, 0, ax, by, 0, 1, bx, by, 1, 1], dtype="f4")
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
