"""Tests for the visualisation layer: VU meter mapping + placeholder fallback."""

from __future__ import annotations

import numpy as np

from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.visuals import Features, PlaceholderVisual, VuMeter


def _drive(vu, model, level, n=120, t0=0.0, dt=1 / 60):
    """Run the VU meter for n frames at a constant level; return next t."""
    t = t0
    for _ in range(n):
        t += dt
        vu.update(model, t, Features(level=level))
    return t


def _lit_fraction(model):
    return float((model.colors.sum(axis=1) > 0).mean())


def test_fill_fraction_tracks_level():
    model = build_model(CubeConfig())
    vu = VuMeter(model)

    _drive(vu, model, 0.0)
    assert _lit_fraction(model) < 0.05  # silence -> dark

    _drive(vu, model, 1.0)
    assert _lit_fraction(model) > 0.9  # full -> nearly all lit

    _drive(vu, model, 0.5)
    assert 0.3 < _lit_fraction(model) < 0.7  # ~half height


def test_colour_ramps_green_floor_red_top():
    model = build_model(CubeConfig())
    vu = VuMeter(model)
    _drive(vu, model, 1.0)
    colors = model.colors
    low = (vu.height < 0.2) & (colors.sum(axis=1) > 0)
    high = (vu.height > 0.8) & (colors.sum(axis=1) > 0)
    # Near the floor: green > red; near the top: red > green.
    assert colors[low][:, 1].mean() > colors[low][:, 0].mean()
    assert colors[high][:, 0].mean() > colors[high][:, 1].mean()


def test_release_decays_gradually():
    model = build_model(CubeConfig())
    vu = VuMeter(model)
    t = _drive(vu, model, 1.0)  # settle high
    assert vu.disp > 0.95
    # One frame at level 0 should drop only a little (slow release).
    t += 1 / 60
    vu.update(model, t, Features(level=0.0))
    assert vu.disp > 0.8
    # After ~1 s it should be much lower.
    _drive(vu, model, 0.0, n=60, t0=t)
    assert vu.disp < 0.3


def test_placeholder_visual_writes_buffer():
    model = build_model(CubeConfig())
    vis = PlaceholderVisual()
    vis.update(model, 1.5, Features())
    assert float(model.colors.sum()) > 0.0
