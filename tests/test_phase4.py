"""Phase 4: event detection (multi-band onset classification + sustain split)."""

from __future__ import annotations

import numpy as np

from cube_dance.audio.events import EventDetector

SR = 44100
WIN = 1024


def _w(sig):
    s = np.asarray(sig, dtype=np.float32)
    return np.stack([s, s], axis=1)


def _tone(freq, amp=0.7):
    t = np.arange(WIN) / SR
    return _w(amp * np.sin(2 * np.pi * freq * t))


def _kinds(events):
    return [e.kind for e in events]


def test_classifies_kick_hat_snare():
    silence = _w(np.zeros(WIN))

    d = EventDetector(SR, win=WIN)
    d.process(silence, 1 / 60)
    assert "kick" in _kinds(d.process(_tone(55), 1 / 60)[0])

    d = EventDetector(SR, win=WIN)
    d.process(silence, 1 / 60)
    noise = _w(0.5 * np.random.default_rng(1).standard_normal(WIN))
    assert "hat" in _kinds(d.process(noise, 1 / 60)[0])

    d = EventDetector(SR, win=WIN)
    d.process(silence, 1 / 60)
    assert "snare" in _kinds(d.process(_tone(450), 1 / 60)[0])


def test_sustained_tone_fires_once_not_repeatedly():
    d = EventDetector(SR, win=WIN)
    kick = _tone(55)
    fired = []
    for _ in range(30):
        ev, _ = d.process(kick, 1 / 60)
        fired += _kinds(ev)
    # A sustained tone is a transient once, then flux ~0 -> no kick stream.
    assert fired.count("kick") <= 1
    assert len(fired) <= 2


def test_strength_in_range_and_events_are_dataclass():
    d = EventDetector(SR, win=WIN)
    d.process(_w(np.zeros(WIN)), 1 / 60)
    ev, phase = d.process(_tone(55), 1 / 60)
    assert ev and 0.0 <= ev[0].strength <= 1.0
    assert 0.0 <= phase <= 1.0


# --- Element engine + presets ------------------------------------------------
from cube_dance.audio.events import Event  # noqa: E402
from cube_dance.config import CubeConfig  # noqa: E402
from cube_dance.led_topology import build_model  # noqa: E402
from cube_dance.visuals import Features  # noqa: E402
from cube_dance.visuals.engine import VisualEngine  # noqa: E402
from cube_dance.visuals.engine.elements import KickPulse, SpectrumBeams  # noqa: E402
from cube_dance import presets  # noqa: E402


def test_engine_composites_elements():
    m = build_model(CubeConfig())
    eng = VisualEngine(m, n_buckets=8)
    eng.add(SpectrumBeams(m, 8))
    nb = 8
    f = Features(level=0.8, buckets_l=np.ones(nb), buckets_r=np.ones(nb))
    eng.update(m, 0.0, f)
    eng.update(m, 1 / 60, f)
    assert float(m.colors[m.edge_mask].sum()) > 0.0


def test_kick_event_triggers_pulse_then_decays():
    m = build_model(CubeConfig())
    eng = VisualEngine(m, n_buckets=8)
    eng.add(KickPulse(m, region="corners", gain=1.0, release=0.12))

    eng.update(m, 0.0, Features())  # no events -> dark
    base = float(m.colors[m.corner_mask].sum())
    eng.update(m, 1 / 60, Features(events=[Event("kick", 1.0)]))
    hit = float(m.colors[m.corner_mask].sum())
    assert hit > base + 1.0  # kick lit the corners

    for i in range(40):  # decays with no further kicks
        eng.update(m, (2 + i) / 60, Features())
    assert float(m.colors[m.corner_mask].sum()) < hit * 0.2


def test_preset_load_and_unknown():
    m = build_model(CubeConfig())
    eng = VisualEngine(m, n_buckets=8)
    presets.load("deep", eng)
    assert len(eng.elements) > 0
    import pytest

    with pytest.raises(ValueError):
        presets.load("does_not_exist", VisualEngine(m, n_buckets=8))


def test_evolution_advances_under_energy():
    m = build_model(CubeConfig())
    eng = VisualEngine(m, n_buckets=8)
    eng.vparams.hue_drift_base = 0.05
    loud = Features(level=1.0, buckets_l=np.ones(8), buckets_r=np.ones(8))
    t = 0.0
    for _ in range(120):
        t += 1 / 60
        eng.update(m, t, loud)
    assert eng._hue > 0.0 and eng._energy > 0.3
