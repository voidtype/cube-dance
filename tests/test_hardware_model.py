"""Tests for the Phase-3 HardwareCubeModel: interface, geometry, drop-in engine."""

from __future__ import annotations

import numpy as np

from cube_dance.config import CubeConfig
from cube_dance.hardware.artnet import ArtNetSink
from cube_dance.hardware.mapping import build_mapping
from cube_dance.hardware.model import HardwareCubeModel, build_hardware_model
from cube_dance.led_topology import CubeModel
from cube_dance.visuals.base import Features
from cube_dance.visuals.engine import VisualEngine
from cube_dance import presets


def test_exposes_cubemodel_interface():
    m = build_hardware_model()
    # Every attribute the engine + effects read from CubeModel must exist.
    for attr in ("cfg", "positions", "normal", "group", "element_id", "param",
                 "colors", "edge_mask", "corner_mask", "edge_indices",
                 "corner_indices", "region_indices", "run_spans"):
        assert hasattr(m, attr), f"missing {attr}"
    assert m.n == m.positions.shape[0]
    assert m.colors.shape == (m.n, 3)
    assert m.normal.shape == (m.n, 3)
    assert m.param.shape == (m.n,)


def test_pixel_count_and_order_match_artnet_sink():
    mapping = build_mapping()
    model = HardwareCubeModel(mapping)
    sink = ArtNetSink(mapping, host="127.0.0.1")
    # Same canonical order => the colour buffer the model writes is exactly what
    # the sink packs, row for row.
    assert model.n == sink.n_leds == mapping.total_leds()
    assert model.n > 9000  # corners + accents + the synthesised beams/columns
    assert model.fixture_slices == sink.layout.fixture_slices


def test_geometry_is_sane():
    m = build_hardware_model()
    h = m.cfg.half
    # All pixels sit within the cube bounding box (with a hair of float slack).
    assert np.all(m.positions >= -h - 1e-3)
    assert np.all(m.positions <= h + 1e-3)
    # Normals are unit length.
    norms = np.linalg.norm(m.normal, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)
    # Both groups present; ids in range.
    assert m.edge_mask.any() and m.corner_mask.any()
    assert m.element_id[m.corner_mask].max() < 8
    assert m.element_id[m.edge_mask].max() < 12


def test_helpers_and_effects_run_on_hardware_model():
    from cube_dance.visuals.engine.effects import _u01, _pn, _edge_sequence

    m = build_hardware_model()
    assert _u01(m).shape == (m.n, 3)
    assert _pn(m).shape == (m.n, 3)
    seq = _edge_sequence(m)  # ordered edge path
    assert seq.ndim == 1 and seq.size == int(m.edge_mask.sum())


def _features(nb=8):
    rng = np.random.default_rng(0)
    return Features(
        level=0.5, bass=0.6, mid=0.4, treble=0.3, bass_l=0.5, bass_r=0.5,
        buckets_l=rng.random(nb).astype(np.float32),
        buckets_r=rng.random(nb).astype(np.float32),
        events=[], beat=0.25, wave=rng.standard_normal((64, 2)).astype(np.float32),
    )


def test_engine_drives_hardware_model_and_packs_to_artnet():
    mapping = build_mapping()
    model = HardwareCubeModel(mapping)
    engine = VisualEngine(model, n_buckets=8)
    presets.load("minimal", engine)

    feats = _features()
    for i in range(5):
        engine.update(model, t=i * 0.05, features=feats)

    assert np.all(np.isfinite(model.colors))
    assert model.colors.min() >= 0.0 and model.colors.max() <= 1.0
    # Something actually lit up.
    assert model.colors.max() > 0.0

    # The exact buffer the engine produced packs cleanly to ArtNet.
    sink = ArtNetSink(mapping, host="127.0.0.1")
    packets = sink.pack(model.colors)
    assert len(packets) == len(sink.layout.universes)


def test_a_few_geometry_presets_build_and_render():
    """Structure-aware presets that read positions/edges/normals must not crash."""
    mapping = build_mapping()
    feats = _features()
    for name in ("atlas", "snake", "life", "sun", "plasma", "lacing"):
        model = HardwareCubeModel(mapping)
        engine = VisualEngine(model, n_buckets=8)
        presets.load(name, engine)
        engine.update(model, t=0.1, features=feats)
        engine.update(model, t=0.2, features=feats)
        assert np.all(np.isfinite(model.colors)), f"{name} produced non-finite output"


def test_structural_mask_marks_beams_only():
    m = build_hardware_model()
    assert m.structural_mask.shape == (m.n,)
    # The synthesised beams/columns: 72 strips x 119 LEDs.
    assert int(m.structural_mask.sum()) == 72 * 119
    # Real corner panels + edge accents are not structural.
    assert not m.structural_mask.all() and m.structural_mask.any()
    # Structural pixels are all on edges (beams/columns), never corner panels.
    assert not m.corner_mask[m.structural_mask].any()


def test_shares_cubeconfig_with_sim():
    # The hardware model uses the same physical config the sim does, so geometry
    # helpers (half, side_m) line up.
    m = build_hardware_model()
    assert isinstance(m.cfg, CubeConfig)
    sim = CubeModel(m.cfg)
    assert m.cfg.half == sim.cfg.half
