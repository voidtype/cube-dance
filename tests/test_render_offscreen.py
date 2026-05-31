"""Offscreen GPU render test.

Exercises the full render path (programs, VAOs, dynamic color buffer, draw
calls, camera matrices) by rendering into a framebuffer -- no window required.
Skips cleanly on machines without an available GL context (e.g. headless CI).
"""

from __future__ import annotations

import math

import numpy as np
import pytest


def _standalone_ctx():
    try:
        import moderngl as mgl

        return mgl.create_standalone_context(require=330)
    except Exception as exc:  # pragma: no cover - platform dependent
        pytest.skip(f"no standalone GL context available: {exc}")


def test_scene_renders_lit_pixels_offscreen():
    from cube_dance.config import CubeConfig
    from cube_dance.led_topology import build_model
    from cube_dance.patterns import PlaceholderPattern
    from cube_dance.render.camera import OrbitCamera
    from cube_dance.render.scene import CubeScene

    ctx = _standalone_ctx()
    try:
        w = h = 256
        fbo = ctx.framebuffer(
            color_attachments=[ctx.texture((w, h), 3)],
            depth_attachment=ctx.depth_renderbuffer((w, h)),
        )
        fbo.use()

        cfg = CubeConfig()
        model = build_model(cfg)
        PlaceholderPattern().apply(model, 0.7)
        scene = CubeScene(ctx, model)
        scene.update_colors()

        cam = OrbitCamera(distance=cfg.half * math.sqrt(3) / math.sin(math.radians(22.5)) * 1.15)
        cam.aspect = w / h
        ps = CubeScene.proj_scale(h, cam.fovy_deg)

        fbo.clear(0.02, 0.02, 0.03)
        scene.render(cam.view_bytes(), cam.proj_bytes(), ps)

        data = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(h, w, 3)
        lit = data.astype(int).sum(axis=2) > (5 + 5 + 7) + 30
        assert int(lit.sum()) > 200  # the cube actually drew something
    finally:
        ctx.release()
