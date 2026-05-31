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
