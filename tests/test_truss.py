"""Tests for per-pixel normals and the truss mesh."""

from __future__ import annotations

import numpy as np

from cube_dance.config import CubeConfig
from cube_dance.geometry import build_corners, build_edges
from cube_dance.led_topology import build_model
from cube_dance.truss import build_truss, cylinder


def test_normals_unit_length_and_oriented():
    cfg = CubeConfig()
    m = build_model(cfg)
    assert m.normal.shape == m.positions.shape
    assert np.allclose(np.linalg.norm(m.normal, axis=1), 1.0, atol=1e-5)

    # Edge normals are perpendicular to their edge run.
    edge_axis = {e.index: e.axis for e in build_edges()}
    for i in np.where(m.edge_mask)[0][::101]:
        assert abs(m.normal[i, edge_axis[int(m.element_id[i])]]) < 1e-5

    # Corner normals point away from the corner-cube centre.
    mid = (cfg.edge_half + cfg.half) / 2.0
    centre = {c.index: np.array(c.signs) * mid for c in build_corners()}
    for i in np.where(m.corner_mask)[0][::101]:
        c = centre[int(m.element_id[i])]
        assert np.dot(m.normal[i], m.positions[i] - c) > 0.0


def test_cylinder_and_truss_shapes():
    p, n = cylinder([0, 0, 0], [0, 1, 0], 0.02)
    assert p.shape == n.shape and p.shape[0] > 0 and p.shape[0] % 3 == 0

    cfg = CubeConfig()
    tp, tn = build_truss(cfg)
    assert tp.shape == tn.shape and tp.shape[0] > 0
    assert np.isfinite(tp).all() and np.isfinite(tn).all()
    # The truss stays within the cube bounds (plus a little for tube radius).
    assert tp.min() > -cfg.half - 0.05 and tp.max() < cfg.half + 0.05


def test_chord_tubes_lie_under_led_chords():
    cfg = CubeConfig()
    m = build_model(cfg)
    tp, _ = build_truss(cfg)
    # An edge LED pixel must be within ~a tube radius of some chord-tube vertex.
    idx = np.where(m.edge_mask)[0][1000]
    p = m.positions[idx]
    dmin = np.sqrt(((tp - p) ** 2).sum(axis=1)).min()
    assert dmin < 0.05
