"""Phase 2: frequency bands, spatial regions, and the cube-aware visual."""

from __future__ import annotations

import numpy as np

from cube_dance.audio.file import AudioFile
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.visuals import CubeAwareVisual, Features


def _sine(freq, sr=44100, dur=1.0, chans=2, amp=0.5):
    t = np.arange(int(sr * dur)) / sr
    s = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([s] * chans, axis=1)


def test_bands_separate_frequency_content():
    bass = AudioFile.from_array(_sine(60), 44100)
    treble = AudioFile.from_array(_sine(8000), 44100)
    b = bass.bands_at(0.5)
    h = treble.bands_at(0.5)
    assert b["bass"] > b["treble"]
    assert h["treble"] > h["bass"]


def test_bands_left_right_split():
    sr = 44100
    s = (0.6 * np.sin(2 * np.pi * 60 * np.arange(sr) / sr)).astype(np.float32)
    stereo = np.stack([s, np.zeros_like(s)], axis=1)  # bass only in left
    af = AudioFile.from_array(stereo, sr)
    bd = af.bands_at(0.5)
    assert bd["bass_l"] > bd["bass_r"]


def test_region_indices_partition():
    m = build_model(CubeConfig())
    for lo, hi in (("left", "right"), ("bottom", "top"), ("back", "front")):
        a, b = m.region_indices[lo], m.region_indices[hi]
        union = np.union1d(a, b)
        assert union.size == m.n
        assert np.intersect1d(a, b).size == 0


def _settle(vis, model, feats, n=40):
    for i in range(n):
        vis.update(model, i / 60.0, feats)


def _mean_brightness(model, mask):
    sel = model.colors[mask]
    return float(sel.sum(axis=1).mean()) if sel.size else 0.0


def test_cube_aware_bass_lights_corners_treble_lights_beams():
    m = build_model(CubeConfig())

    vis = CubeAwareVisual(m)
    _settle(vis, m, Features(bass=1.0, bass_l=1.0, bass_r=1.0, mid=0.0, treble=0.0))
    assert _mean_brightness(m, m.corner_mask) > _mean_brightness(m, m.edge_mask)

    vis = CubeAwareVisual(m)
    _settle(vis, m, Features(bass=0.0, bass_l=0.0, bass_r=0.0, mid=0.0, treble=1.0))
    assert _mean_brightness(m, m.edge_mask) > _mean_brightness(m, m.corner_mask)


def test_cube_aware_stereo_splits_left_right_corners():
    m = build_model(CubeConfig())
    x = m.positions[:, 0]
    left_corners = m.corner_mask & (x < 0)
    right_corners = m.corner_mask & (x >= 0)
    vis = CubeAwareVisual(m)
    _settle(vis, m, Features(bass_l=1.0, bass_r=0.0))
    assert _mean_brightness(m, left_corners) > _mean_brightness(m, right_corners)
