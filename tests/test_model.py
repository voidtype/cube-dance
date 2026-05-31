"""Tests for the cube model: geometry, topology, addressing, regions, buffer."""

from __future__ import annotations

import numpy as np
import pytest

from cube_dance.config import CubeConfig
from cube_dance.geometry import build_corners, build_edges, edge_chord_rows, is_base_edge
from cube_dance.led_topology import GROUP_CORNER, GROUP_EDGE, build_model


def test_edge_and_corner_counts():
    assert len(build_edges()) == 12
    assert len(build_corners()) == 8


def test_cube_extents_match_reference():
    cfg = CubeConfig()
    model = build_model(cfg)
    assert np.allclose(model.positions.min(axis=0), -cfg.half, atol=1e-3)
    assert np.allclose(model.positions.max(axis=0), cfg.half, atol=1e-3)


def test_base_edges_have_two_rows_others_three():
    cfg = CubeConfig()
    for e in build_edges():
        rows = len(edge_chord_rows(e, cfg))
        assert rows == (2 if is_base_edge(e) else 3)


def test_total_edge_pixels_follow_density_and_rows():
    cfg = CubeConfig(edge_leds_per_m=50.0, corner_leds_per_m=120.0)
    model = build_model(cfg)
    per_row = int(round(cfg.edge_leds_per_m * cfg.edge_run_m))  # 100
    total_rows = sum(len(edge_chord_rows(e, cfg)) for e in build_edges())
    assert cfg.edge_pixel_count() == per_row
    assert int(model.edge_mask.sum()) == total_rows * per_row


def test_edge_pixels_lie_on_chord_rows_within_span():
    cfg = CubeConfig()
    model = build_model(cfg)
    for edge in build_edges():
        idx = model.edge_indices[edge.index]
        pts = model.positions[idx].astype(np.float64)
        rows = edge_chord_rows(edge, cfg)
        dmin = np.full(len(pts), np.inf)
        for a, b in rows:
            ab = b - a
            t = np.clip((pts - a) @ ab / (ab @ ab), 0.0, 1.0)
            proj = a + t[:, None] * ab
            dmin = np.minimum(dmin, np.linalg.norm(pts - proj, axis=1))
        assert dmin.max() < 1e-3  # every pixel sits on one of the chord rows
        assert np.abs(pts[:, edge.axis]).max() <= cfg.edge_half + 1e-6


def test_base_edges_skip_vertical_faces():
    """Base (floor) edges must not light a ground-facing or up-facing row."""
    cfg = CubeConfig()
    model = build_model(cfg)
    for edge in build_edges():
        if not is_base_edge(edge):
            continue
        pts = model.positions[model.edge_indices[edge.index]]
        # The horizontal axis perpendicular to the edge is the lit (outer) face;
        # all rows must sit at the outer offset on that axis (|coord| ~ half).
        perp = [d for d in (0, 1, 2) if d != edge.axis and d != 1][0]  # the non-Y perpendicular
        assert np.allclose(np.abs(pts[:, perp]), cfg.half, atol=1e-6)


def test_corners_are_denser_than_edges():
    cfg = CubeConfig()
    edge_spacing = cfg.edge_run_m / (cfg.edge_pixel_count() - 1)
    corner_spacing = (cfg.corner_m * 2**0.5) / (cfg.corner_diagonal_pixel_count() - 1)
    assert corner_spacing < edge_spacing


def test_each_corner_has_outline_and_x_panels():
    cfg = CubeConfig()
    model = build_model(cfg)
    expected = 12 * cfg.corner_edge_pixel_count() + 2 * cfg.corner_x_faces * cfg.corner_diagonal_pixel_count()
    for corner in build_corners():
        idx = model.corner_indices[corner.index]
        assert idx.size == expected
        pts = model.positions[idx]
        centered = pts - pts.mean(axis=0)
        assert np.linalg.matrix_rank(centered, tol=1e-4) >= 2


def test_addressing_is_deterministic():
    cfg = CubeConfig()
    a, b = build_model(cfg), build_model(cfg)
    assert a.n == b.n
    assert np.array_equal(a.positions, b.positions)
    assert np.array_equal(a.group, b.group)
    assert np.array_equal(a.element_id, b.element_id)


def test_index_space_is_contiguous_and_partitioned():
    model = build_model(CubeConfig())
    all_idx = np.concatenate([*model.edge_indices.values(), *model.corner_indices.values()])
    all_idx.sort()
    assert np.array_equal(all_idx, np.arange(model.n))
    assert int((model.edge_mask & model.corner_mask).sum()) == 0
    assert int((model.edge_mask | model.corner_mask).sum()) == model.n


def test_every_pixel_has_exactly_one_element():
    model = build_model(CubeConfig())
    for i in range(0, model.n, 137):
        if model.group[i] == GROUP_EDGE:
            assert 0 <= model.element_id[i] <= 11
        else:
            assert model.group[i] == GROUP_CORNER
            assert 0 <= model.element_id[i] <= 7


def test_color_buffer_contract():
    model = build_model(CubeConfig())
    assert model.colors.shape == (model.n, 3)
    assert model.colors.dtype == np.float32
    assert float(model.colors.sum()) == 0.0
    model.colors[5] = (1.0, 0.5, 0.25)
    assert np.allclose(model.colors[5], (1.0, 0.5, 0.25))
    assert float(model.colors[:5].sum()) == 0.0
    assert float(model.colors[6:].sum()) == 0.0


def test_corner_density_must_exceed_edge_density():
    with pytest.raises(ValueError):
        CubeConfig(edge_leds_per_m=120.0, corner_leds_per_m=60.0)
