"""The `countdown` preset: the cube counts 10 -> 1 down the frame, then the bells."""

from __future__ import annotations

import numpy as np

from cube_dance import presets
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.visuals import Features
from cube_dance.visuals.engine import VisualEngine
from cube_dance.visuals.engine.context import Context
from cube_dance.visuals.engine.element import Knob, Trigger
from cube_dance.visuals.engine.elements import Countdown

MODEL = build_model(CubeConfig())
_HY = ((MODEL.positions[:, 1] + MODEL.cfg.half) / MODEL.cfg.side_m)
TOP = _HY > 0.75
BOT = _HY < 0.25


def test_registered_with_start_button():
    assert "countdown" in presets.PRESET_ORDER
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load("countdown", eng)
    assert 1 <= len(eng.knob_spec) <= 4 and all(isinstance(k, Knob) for k in eng.knob_spec)
    labels = list(eng.triggers)
    assert "START" in labels                                   # the button
    assert all(isinstance(t, Trigger) for t in eng.triggers.values())


def test_idle_renders_but_is_calm():
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load("countdown", eng)
    f = Features(level=0.5, bass=0.5, mid=0.4, treble=0.3, bass_l=0.5, bass_r=0.5)
    out = np.zeros((MODEL.n, 3), np.float32)
    for i in range(20):
        eng.render(MODEL, i / 60, f, out)
    assert out.sum() > 0.0                                     # not dead
    assert out.mean() < 0.4                                     # but calm — nowhere near the burst


def _run_element(dur=10.0, burst=4.5, steps=200):
    cd = Countdown(MODEL, dur=dur, burst=burst)
    rows = []
    for _ in range(steps):
        out = np.zeros((MODEL.n, 3), np.float32)
        cd.apply(Context(MODEL, 0.0, 0.1, None), out)          # each apply advances 0.1s
        rows.append((cd._t, float(out.sum()), float(out[TOP].sum()), float(out[BOT].sum())))
        if cd.done:
            break
    return cd, rows


def test_counts_down_then_bursts_then_finishes():
    cd, rows = _run_element()

    # the column drains: late in the count the lit band sits LOW (bottom >> top)
    late = [r for r in rows if 8.2 <= r[0] <= 8.8 and abs((r[0] % 1.0) - 0.5) < 0.18]
    assert late, "no late-countdown sample captured"
    assert late[0][3] > late[0][2] * 1.5                       # bottom brighter than top

    # early in the count the top is lit (the column is tall)
    early = [r for r in rows if 1.2 <= r[0] <= 1.8 and abs((r[0] % 1.0) - 0.5) < 0.18]
    assert early and early[0][2] > 0.0

    # the bells: the brightest frame lands right after the 10s count
    peak = max(rows, key=lambda r: r[1])
    assert 9.8 <= peak[0] <= 12.5, f"burst peaked at t={peak[0]:.1f}"
    countdown_mean = np.mean([r[1] for r in rows if r[0] < 9.0])
    assert peak[1] > countdown_mean * 2.0                      # the blast clearly dominates

    # and it cleans itself up
    assert cd.done and rows[-1][0] <= 15.5


def test_burst_mode_fires_immediately():
    cd, rows = _run_element(dur=0.0, burst=4.5)
    assert rows[0][1] > 0.0                                    # lit on the first frame (no wait)
    assert cd.done and rows[-1][0] <= 5.5


def test_start_trigger_through_the_engine():
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load("countdown", eng)
    f = Features(level=0.4, bass=0.4, mid=0.3, treble=0.3, bass_l=0.4, bass_r=0.4)
    out = np.zeros((MODEL.n, 3), np.float32)
    eng.render(MODEL, 0.0, f, out)                            # establish dt baseline
    eng.fire("START")
    lit = []
    for i in range(1, 200):
        out[:] = 0
        eng.render(MODEL, i * 0.1, f, out)
        lit.append(float(out.sum()))
        if not eng.transients:
            break
    assert max(lit) > 0.0                                      # the countdown drew
    assert not eng.transients                                 # and expired on its own
