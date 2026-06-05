"""Render a 7-act storyboard contact sheet of the DUSTLIGHT show.

Drives the real DeckMixer + RaveShow director through each act, renders the cube
offscreen, and lays the seven frames out with labels. Saves a PNG.

    uv run python tools/render_storyboard.py [out.png]
"""

from __future__ import annotations

import math
import sys

import numpy as np

from cube_dance.audio.events import Event
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.render.camera import OrbitCamera
from cube_dance.render.scene import CubeScene
from cube_dance.show import DUSTLIGHT, RaveShow
from cube_dance.visuals import Features
from cube_dance.visuals.engine.mixer import DeckMixer

RW, RH = 760, 600          # per-act render resolution
TW, TH = 520, 410          # per-act tile in the sheet (render is downscaled in)
COLS = 4
PADX, PADY = 16, 16
HEADER = 92
LABEL = 64


def _feats(act_idx: int, vt: float) -> Features:
    # an energy curve that mirrors the night: quiet arrival -> peak -> dawn
    energy = [0.52, 0.62, 0.74, 0.98, 0.80, 0.62, 0.84][act_idx]
    # peaked spectrum (only some bands hot), phase-shifted per act so the lit
    # structure differs from act to act instead of a uniform rainbow
    base = np.abs(np.sin(np.linspace(0.2, 3.0, 8) + vt * 1.6 + act_idx * 1.3))
    shp = 0.12 + 0.88 * base ** 3
    buckets = (energy * shp).astype(np.float32)
    events = None
    beat = (vt * 2.2) % 1.0
    if act_idx in (2, 3):  # build + peak have a driving kick
        if (vt % 0.46) < 0.05:
            events = [Event("kick", 0.95 if act_idx == 3 else 0.7)]
    return Features(
        level=energy, bass=energy * 0.92, mid=energy * 0.7, treble=energy * 0.5,
        bass_l=energy * 0.9, bass_r=energy * 0.85,
        buckets_l=buckets, buckets_r=(buckets * 0.92).astype(np.float32),
        events=events, beat=beat,
    )


def _standalone_ctx():
    import moderngl as mgl

    return mgl.create_standalone_context(require=330)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/dustlight-storyboard.png"
    try:
        ctx = _standalone_ctx()
    except Exception as exc:  # pragma: no cover
        print(f"no standalone GL context: {exc}")
        return 1

    # The Monolith glowing in the dark — no scenery, just the emissive wireframe.
    cfg = CubeConfig(show_floor=False, show_speakers=False, show_bushes=False, show_truss=False)
    model = build_model(cfg)
    scene = CubeScene(ctx, model, led_radius_m=0.016, ambient=0.0)

    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((RW, RH), 3)],
        depth_attachment=ctx.depth_renderbuffer((RW, RH)),
    )

    cam = OrbitCamera(distance=cfg.half * math.sqrt(3) / math.sin(math.radians(22.5)) * 0.66)
    cam.azimuth_deg = 36.0
    cam.elevation_deg = 15.0
    cam.aspect = RW / RH
    ps = CubeScene.proj_scale(RH, cam.fovy_deg)

    mix = DeckMixer(model, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    # For a legible contact sheet, let each act render its presets at full
    # brightness (the act *volumes* still define its character); the global
    # dim-into-the-night belongs to the live show, not the thumbnails.
    show.drive_master = False
    show.drive_knobs = False
    seg = show.duration / show.n_acts

    tiles: list[np.ndarray] = []
    for ai, act in enumerate(DUSTLIGHT):
        clock = seg * (ai + 0.55)  # mid-act, past the crossfade
        vt = 0.0
        for k in range(64):  # warm up evolving presets + settle the crossfade
            vt += 1 / 60
            show.apply(clock)            # hold this act (clock fixed -> volumes steady)
            mix.update(model, vt, _feats(ai, vt))
        scene.update_colors()
        fbo.use()
        fbo.clear(0.015, 0.015, 0.022)
        scene.render(cam.view_bytes(), cam.proj_bytes(), ps)
        buf = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(RH, RW, 3)
        tiles.append(np.flipud(buf).copy())  # GL origin is bottom-left
        lit = buf.astype(int).sum(2) > 60
        print(f"  {ai+1}. {act.name:<13} {act.clock:>7}  lit={int(lit.sum()):6d}  "
              f"{' · '.join(p or '—' for p in act.presets)}")
    ctx.release()

    _compose(tiles, out)
    print(f"\nstoryboard -> {out}")
    return 0


def _compose(tiles: list[np.ndarray], out: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    rows = (len(tiles) + COLS - 1) // COLS
    W = COLS * TW + (COLS + 1) * PADX
    H = HEADER + rows * (TH + LABEL) + (rows + 1) * PADY
    sheet = Image.new("RGB", (W, H), (8, 8, 12))
    draw = ImageDraw.Draw(sheet)

    def font(sz: int):
        for path in (
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ):
            try:
                return ImageFont.truetype(path, sz)
            except Exception:
                pass
        return ImageFont.load_default()

    f_title, f_sub, f_act, f_clock, f_deck = font(46), font(20), font(26), font(19), font(15)
    draw.text((PADX + 2, 22), "DUSTLIGHT", font=f_title, fill=(255, 196, 120))
    draw.text((PADX + 4, 70), "a night on the Monolith — the cube performs the seven acts, dusk to sunrise",
              font=f_sub, fill=(150, 150, 165))

    for i, tile in enumerate(tiles):
        act = DUSTLIGHT[i]
        r, c = divmod(i, COLS)
        x = PADX + c * (TW + PADX)
        y = HEADER + PADY + r * (TH + LABEL + PADY)
        img = Image.fromarray(tile).resize((TW, TH), Image.LANCZOS)
        sheet.paste(img, (x, y))
        # accent rule + labels under the frame
        draw.rectangle([x, y + TH, x + TW, y + TH + LABEL], fill=(14, 14, 20))
        draw.line([x, y + TH, x + TW, y + TH], fill=(60, 60, 80))
        draw.text((x + 10, y + TH + 6), f"{i+1}. {act.name}", font=f_act, fill=(255, 210, 150))
        draw.text((x + TW - 96, y + TH + 11), act.clock, font=f_clock, fill=(150, 160, 180))
        decks = " · ".join(p or "—" for p in act.presets)
        draw.text((x + 10, y + TH + 40), decks, font=f_deck, fill=(120, 170, 160))

    sheet.save(out)


if __name__ == "__main__":
    raise SystemExit(main())
