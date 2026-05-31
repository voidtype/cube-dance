"""The headless self-test must run, validate the buffer, and never open a window."""

from __future__ import annotations

import numpy as np

from cube_dance.cli import main
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.patterns import PlaceholderPattern
from cube_dance.selftest import run_selftest


def test_selftest_runs_headless():
    assert run_selftest(frames=10, cfg=CubeConfig(), verbose=False) == 0


def test_cli_selftest_path():
    # Exercises argument parsing + the headless branch; opens no window.
    assert main(["--selftest", "--frames", "5"]) == 0


def test_placeholder_pattern_distinguishes_groups_over_time():
    model = build_model(CubeConfig())
    pattern = PlaceholderPattern()

    pattern.apply(model, 0.0)
    edges_t0 = model.colors[model.edge_mask].copy()

    pattern.apply(model, 1.5)
    edges_t1 = model.colors[model.edge_mask].copy()

    # Colors evolve over time (the pattern animates).
    assert not np.allclose(edges_t0, edges_t1)
    # Buffer stays within [0, 1].
    assert float(model.colors.min()) >= 0.0
    assert float(model.colors.max()) <= 1.0
    # Both groups are driven (non-zero), i.e. edges and corners both render.
    assert float(model.colors[model.edge_mask].sum()) > 0.0
    assert float(model.colors[model.corner_mask].sum()) > 0.0
