"""Phase 2: streaming spectrum analysis, AGC, regions, cube-aware visual."""

from __future__ import annotations

import numpy as np

from cube_dance.audio.analysis import SpectrumAnalyzer
from cube_dance.audio.processor import FeatureProcessor
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.visuals import CubeAwareVisual, Features

SR = 44100


def _win(an, freq, chans=2, amp=0.6):
    t = np.arange(an.win) / SR
    s = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([s] * chans, axis=1) if chans == 2 else s[:, None]


def test_analyzer_separates_frequencies_and_channels():
    an = SpectrumAnalyzer(SR, n_buckets=8)
    bl, _ = an.analyze(_win(an, 60))
    assert bl[0] > bl[-1]  # bass sine -> low bucket loudest
    bl, _ = an.analyze(_win(an, 9000))
    assert bl[-1] > bl[0]  # treble sine -> high bucket loudest

    t = np.arange(an.win) / SR
    s = (0.6 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
    left_only = np.stack([s, np.zeros_like(s)], axis=1)
    bl, br = an.analyze(left_only)
    assert bl[0] > br[0]


def test_agc_hides_quiet_sections_and_levels_loud():
    an = SpectrumAnalyzer(SR, n_buckets=8)
    loud = _win(an, 60, amp=0.6)
    quiet = _win(an, 60, amp=0.01)

    p = FeatureProcessor(an)
    for _ in range(20):  # loud passage sets the references
        f_loud = p.process(loud, 1 / 60)
    for _ in range(20):  # then a quiet section in the SAME stream
        f_quiet = p.process(quiet, 1 / 60)

    assert f_loud.bass > 0.3
    assert f_quiet.bass < 0.5 * f_loud.bass  # quiet section hidden exponentially
    assert f_loud.buckets_l is not None and f_loud.buckets_l.shape == (8,)


def test_agc_levels_quiet_track_on_its_own():
    """A track that is quiet throughout still fills the range (auto-level)."""
    an = SpectrumAnalyzer(SR, n_buckets=8)
    p = FeatureProcessor(an)
    quiet = _win(an, 60, amp=0.05)
    for _ in range(40):
        f = p.process(quiet, 1 / 60)
    assert f.bass > 0.3  # adapts to its own level


def test_region_indices_partition():
    m = build_model(CubeConfig())
    for lo, hi in (("left", "right"), ("bottom", "top"), ("back", "front")):
        a, b = m.region_indices[lo], m.region_indices[hi]
        assert np.union1d(a, b).size == m.n
        assert np.intersect1d(a, b).size == 0


def _bright(model, mask):
    sel = model.colors[mask]
    return float(sel.sum(axis=1).mean()) if sel.size else 0.0


def _settle(vis, model, feats, n=8):
    for i in range(n):
        vis.update(model, i / 60.0, feats)


def test_cube_aware_bass_corners_split_left_right():
    m = build_model(CubeConfig())
    nb = 8
    x = m.positions[:, 0]
    left_c = m.corner_mask & (x < 0)
    right_c = m.corner_mask & (x >= 0)
    vis = CubeAwareVisual(m, n_buckets=nb)
    _settle(vis, m, Features(bass_l=1.0, bass_r=0.0, buckets_l=np.zeros(nb), buckets_r=np.zeros(nb)))
    assert _bright(m, left_c) > _bright(m, right_c)


def test_cube_aware_beams_react_to_buckets():
    m = build_model(CubeConfig())
    nb = 8
    vis = CubeAwareVisual(m, n_buckets=nb)
    _settle(vis, m, Features(buckets_l=np.ones(nb), buckets_r=np.ones(nb)))
    on = _bright(m, m.edge_mask)
    vis2 = CubeAwareVisual(m, n_buckets=nb)
    vis2.update(m, 0.0, Features(buckets_l=np.zeros(nb), buckets_r=np.zeros(nb)))
    off = _bright(m, m.edge_mask)
    assert on > 0.3 and off < 0.05
