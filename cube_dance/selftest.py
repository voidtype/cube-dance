"""Headless self-test: validate the data path with no window/display.

Builds the model, advances the placeholder pattern for N frames, prints stats,
and attempts a best-effort offscreen shader-compile check (skipped cleanly if no
GL context is available, e.g. a headless CI box).
"""

from __future__ import annotations

import time as _time

from .config import CubeConfig
from .led_topology import build_model
from .patterns import PlaceholderPattern


def _offscreen_shader_check(verbose: bool) -> None:
    try:
        import moderngl as mgl

        from .render.scene import (
            LED_STRIP_FRAGMENT_SHADER,
            LED_STRIP_VERTEX_SHADER,
            METAL_FRAGMENT_SHADER,
            METAL_VERTEX_SHADER,
            SOLID_FRAGMENT_SHADER,
            SOLID_VERTEX_SHADER,
        )

        ctx = mgl.create_standalone_context(require=330)
        ctx.program(vertex_shader=LED_STRIP_VERTEX_SHADER, fragment_shader=LED_STRIP_FRAGMENT_SHADER)
        ctx.program(vertex_shader=SOLID_VERTEX_SHADER, fragment_shader=SOLID_FRAGMENT_SHADER)
        ctx.program(vertex_shader=METAL_VERTEX_SHADER, fragment_shader=METAL_FRAGMENT_SHADER)
        ctx.release()
        if verbose:
            print("[selftest] offscreen shader compile: OK")
    except Exception as exc:  # pragma: no cover - platform dependent
        if verbose:
            print(f"[selftest] offscreen shader compile: skipped ({type(exc).__name__}: {exc})")


def run_selftest(
    frames: int = 120,
    cfg: CubeConfig | None = None,
    audio_file=None,
    visual_choice: str = "auto",
    verbose: bool = True,
) -> int:
    cfg = cfg or CubeConfig()
    model = build_model(cfg)
    dt = 1.0 / 60.0

    levels: list[float] = []
    t0 = _time.perf_counter()
    if audio_file is not None:
        from .audio import AudioSource
        from .visuals import CubeAwareVisual, Features, VuMeter

        source = AudioSource(audio_file, mute=True)  # no device in headless self-test
        source.start()
        visual = VuMeter(model) if visual_choice == "vu" else CubeAwareVisual(model)
        for _ in range(frames):
            source.update(dt)
            feats = Features(level=source.level(), **source.bands())
            levels.append(feats.level)
            visual.update(model, source.position, feats)
        mode = "audio " + ("vu" if visual_choice == "vu" else "spectrum")
    else:
        pattern = PlaceholderPattern()
        for i in range(frames):
            pattern.apply(model, i * dt)
        mode = "placeholder"
    elapsed = _time.perf_counter() - t0

    assert model.colors.shape == (model.n, 3), "color buffer must be (N, 3)"
    assert float(model.colors.min()) >= 0.0 and float(model.colors.max()) <= 1.0

    if verbose:
        per_ms = elapsed / max(frames, 1) * 1000.0
        fps = 1000.0 / per_ms if per_ms > 0 else float("inf")
        print(
            f"[selftest] LED pixels: {model.n} "
            f"(edge {int(model.edge_mask.sum())}, corner {int(model.corner_mask.sum())})"
        )
        print(f"[selftest] color buffer shape: {model.colors.shape}")
        if levels:
            lit = float((model.colors.sum(axis=1) > 0).mean())
            print(
                f"[selftest] audio: level range [{min(levels):.2f}, {max(levels):.2f}], "
                f"final lit fraction {lit:.2f}"
            )
        print(
            f"[selftest] {frames} {mode} frames in {elapsed * 1000:.1f} ms "
            f"({per_ms:.3f} ms/frame, ~{fps:.0f} fps headless)"
        )
        _offscreen_shader_check(verbose)
        print("[selftest] OK")
    else:
        _offscreen_shader_check(False)
    return 0
