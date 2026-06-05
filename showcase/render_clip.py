"""Render the cube reacting to a real song, offscreen, to an H.264 mp4 (muted).

Drives the actual audio-feature pipeline + DeckMixer frame by frame, renders the
Monolith glowing in the dark (no scenery), and pipes raw frames to ffmpeg. A
slow orbit around the cube gives it production polish. Used to make the clips
embedded in the cube-into-2027 pitch page.

    # dial in the look (single PNG):
    uv run python showcase/render_clip.py probe moondance --at 78 --out /tmp/a.png
    # full clip:
    uv run python showcase/render_clip.py clip moondance --start 60 --dur 56 --out showcase/assets/moondance.mp4
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys

import numpy as np

from cube_dance.audio import AudioFile, AudioSource
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.render.camera import OrbitCamera
from cube_dance.render.scene import CubeScene
from cube_dance.visuals.engine.mixer import DeckMixer

MOONDANCE = "/Volumes/underbelly/Consolidated Music/Disc 1/02-Moondance.aiff"
SMOOTH = "/Volumes/underbelly/Consolidated Music/The Best of Sade - 1994/Smooth_Operator_-_Single_Version.aiff"

# A "look" = audio source + a deck recipe (preset, volume, {knob_index: value})
# + camera (az, el, distance-factor) + orbit speed (deg/s) + sync pump.
LOOKS = {
    # Moondance — gentle, flowing, moonlit: aurora curtains and water ripples
    # over a warm ember body. The cube's real output; cooled honestly via the
    # colour knob (evo_hue), not a filter.
    "moondance": {
        "audio": MOONDANCE,
        # speed≈0 locks the hue so it stays moonlit instead of drifting warm;
        # hue at each preset's cool default. A hair of drift for organic shimmer.
        "decks": [("aurora", 0.95, {"speed": 0.05, "hue": 0.0}),
                  ("ripple", 0.55, {"speed": 0.05, "hue": 0.0}),
                  ("ember", 0.5, {"speed": 0.04, "hue": 0.0})],
        "cam": (34.0, 13.0, 0.66), "orbit": 5.0, "sync": False, "radius": 0.017,
    },
    # Smooth Operator — the reveal: genuinely warm presets (inferno + the
    # monolith body + deep bass corners) so the gold comes from the LEDs, pumped
    # on the kick. Slick, not frantic.
    "reveal": {
        "audio": SMOOTH,
        # speed=0 locks the palette gold (no drift to green); hue at each
        # preset's warm base so the reveal stays Sade-gold the whole way.
        "decks": [("inferno", 0.9, {"speed": 0.0, "hue": 0.04}),
                  ("monolith", 0.7, {"speed": 0.0, "hue": 0.03}),
                  ("deep", 0.5, {"speed": 0.0, "hue": 0.05})],
        "cam": (40.0, 11.0, 0.62), "orbit": -8.0, "sync": True, "radius": 0.019,
    },
}


def _build(look_name: str, RW: int, RH: int):
    look = LOOKS[look_name]
    import moderngl as mgl

    ctx = mgl.create_standalone_context(require=330)
    cfg = CubeConfig(show_floor=False, show_speakers=False, show_bushes=False, show_truss=False)
    model = build_model(cfg)
    scene = CubeScene(ctx, model, led_radius_m=look["radius"], ambient=0.0)
    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((RW, RH), 3)],
        depth_attachment=ctx.depth_renderbuffer((RW, RH)),
    )

    audio = AudioFile.load(look["audio"])
    src = AudioSource(audio, mute=True)
    src.playing = True

    names = [d[0] for d in look["decks"]]
    while len(names) < 4:
        names.append(names[-1])
    mix = DeckMixer(model, n_buckets=8, deck_presets=names[:4])
    mix.volumes = [0.0, 0.0, 0.0, 0.0]
    for i, (_, vol, knobs) in enumerate(look["decks"]):
        mix.volumes[i] = vol
        spec = mix.decks[i].knob_spec
        for key, kv in knobs.items():  # address knobs by effect name (e.g. "hue", "speed")
            if isinstance(key, str):
                for j, kb in enumerate(spec):
                    if kb.effect == key:
                        mix.set_knob(i, j, kv)
            else:
                mix.set_knob(i, key, kv)
    mix.vparams.sync_pulse = look["sync"]

    az, el, dist_f = look["cam"]
    cam = OrbitCamera(distance=cfg.half * math.sqrt(3) / math.sin(math.radians(22.5)) * dist_f)
    cam.azimuth_deg, cam.elevation_deg = az, el
    cam.aspect = RW / RH
    ps = CubeScene.proj_scale(RH, cam.fovy_deg)
    return ctx, model, scene, fbo, src, mix, cam, ps, look


def _frame(model, scene, fbo, src, mix, cam, ps, t: float, vt: float, fps: float, orbit: float):
    """One honest frame: real audio features -> real engine -> real LED render.
    The only camera liberty is a slow orbit; no colour post-processing."""
    src._pos = t
    feats = src.features(1.0 / fps)
    cam.azimuth_deg += orbit / fps
    mix.update(model, vt, feats)
    scene.update_colors()
    fbo.use()
    fbo.clear(0.012, 0.012, 0.02)
    scene.render(cam.view_bytes(), cam.proj_bytes(), ps)
    buf = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(fbo.height, fbo.width, 3)
    return np.flipud(buf).copy()  # GL origin is bottom-left — raw cube output


def cmd_probe(a) -> int:
    RW, RH = a.w, a.h
    ctx, model, scene, fbo, src, mix, cam, ps, look = _build(a.look, RW, RH)
    img = None
    # warm up a couple of seconds of audio context so followers settle
    n_warm = int(2.0 * a.fps)
    for k in range(n_warm):
        t = max(0.0, a.at - 2.0) + k / a.fps
        img = _frame(model, scene, fbo, src, mix, cam, ps, t, k / a.fps, a.fps, look["orbit"])
    from PIL import Image

    Image.fromarray(img).save(a.out)
    print(f"probe {a.look} @ {a.at:.1f}s lit={int((img.astype(int).sum(2) > 60).sum())} -> {a.out}")
    ctx.release()
    return 0


def cmd_clip(a) -> int:
    import imageio_ffmpeg

    RW, RH = a.w, a.h
    ctx, model, scene, fbo, src, mix, cam, ps, look = _build(a.look, RW, RH)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
        "-r", str(a.fps), "-i", "-", "-an",
        # mild denoise merges the discrete LED pixels into smooth tape glow and
        # makes the high-frequency detail compressible (encoding only — no colour
        # change, no added effects).
        "-vf", "hqdn3d=3:2:3:3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", str(a.crf),
        "-movflags", "+faststart", a.out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = int(a.dur * a.fps)
    # warm up (settle followers + evolving presets) before the recorded window
    for k in range(int(2.0 * a.fps)):
        _frame(model, scene, fbo, src, mix, cam, ps, max(0.0, a.start - 2.0) + k / a.fps, k / a.fps, a.fps, look["orbit"])
    for i in range(n):
        t = a.start + i / a.fps
        img = _frame(model, scene, fbo, src, mix, cam, ps, t, i / a.fps, a.fps, look["orbit"])
        proc.stdin.write(img.tobytes())
        if i % (a.fps * 5) == 0:
            print(f"  {a.look}: {i/a.fps:5.1f}/{a.dur:.0f}s", flush=True)
    proc.stdin.close()
    proc.wait()
    ctx.release()
    print(f"clip {a.look} [{a.start:.0f}..{a.start+a.dur:.0f}]s -> {a.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("probe")
    pr.add_argument("look", choices=list(LOOKS))
    pr.add_argument("--at", type=float, default=60.0)
    pr.add_argument("--out", default="/tmp/probe.png")
    pr.add_argument("--w", type=int, default=1280)
    pr.add_argument("--h", type=int, default=720)
    pr.add_argument("--fps", type=float, default=30.0)
    pr.set_defaults(func=cmd_probe)
    cl = sub.add_parser("clip")
    cl.add_argument("look", choices=list(LOOKS))
    cl.add_argument("--start", type=float, default=60.0)
    cl.add_argument("--dur", type=float, default=56.0)
    cl.add_argument("--out", required=True)
    cl.add_argument("--w", type=int, default=1280)
    cl.add_argument("--h", type=int, default=720)
    cl.add_argument("--fps", type=float, default=30.0)
    cl.add_argument("--crf", type=int, default=24)
    cl.set_defaults(func=cmd_clip)
    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
