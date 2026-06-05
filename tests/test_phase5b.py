"""Phase 5b: F1 performance surface — preset knob params + pad triggers."""

from __future__ import annotations

import numpy as np

from cube_dance import presets
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.visuals import Features
from cube_dance.visuals.engine import VisualEngine
from cube_dance.visuals.engine.element import Knob, Trigger
from cube_dance.visuals.engine.elements import ColorStab
from cube_dance.visuals.engine.mixer import DeckMixer

MODEL = build_model(CubeConfig())


def _f():
    return Features(level=0.8, bass=0.8, mid=0.6, treble=0.6, bass_l=0.7, bass_r=0.6,
                    buckets_l=np.ones(8, np.float32), buckets_r=np.ones(8, np.float32))


def _mean_rgb(name: str) -> np.ndarray:
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load(name, eng)
    out = np.zeros((MODEL.n, 3), np.float32)
    t = 0.0
    for _ in range(40):
        t += 1 / 60
        eng.render(MODEL, t, _f(), out)
    return out.mean(axis=0)


def test_all_eight_presets_load_and_render():
    assert len(presets.PRESET_ORDER) >= 8
    for name in presets.PRESET_ORDER:
        eng = VisualEngine(MODEL, n_buckets=8)
        presets.load(name, eng)
        out = np.zeros((MODEL.n, 3), np.float32)
        t = 0.0
        for _ in range(20):
            t += 1 / 60
            eng.render(MODEL, t, _f(), out)
        assert out.sum() > 0.0, name


def test_new_presets_are_visually_distinct():
    fire, rain, plas, siren = (_mean_rgb(n) for n in ("inferno", "matrix", "plasma", "siren"))
    assert fire[0] > fire[2] + 0.02          # inferno: warm, red >> blue
    assert rain[1] > rain[0] and rain[1] > rain[2]  # matrix: green dominant
    assert plas.sum() > 0.05                 # plasma: a full colour field
    assert siren.sum() > 0.02                # siren: lit


def test_presets_declare_knobs_and_triggers():
    for name in presets.PRESET_ORDER:
        eng = VisualEngine(MODEL, n_buckets=8)
        presets.load(name, eng)
        assert 1 <= len(eng.knob_spec) <= 4
        assert all(isinstance(k, Knob) for k in eng.knob_spec)
        assert 1 <= len(eng.triggers) <= 4
        assert all(isinstance(t, Trigger) for t in eng.triggers.values())
        # every trigger carries a colour annotation
        for t in eng.triggers.values():
            assert len(t.color) == 3


def test_fire_spawns_transient_then_expires():
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load("punchy", eng)
    label = eng.trigger_order[0]
    out = np.zeros((MODEL.n, 3), np.float32)

    eng.render(MODEL, 0.0, _f(), out)  # establish dt baseline
    eng.fire(label, 1.0)
    assert len(eng.transients) == 1
    eng.render(MODEL, 1 / 60, _f(), out)
    assert out.sum() > 0.0  # the stab is drawing

    for i in range(120):  # decays and is pruned
        eng.render(MODEL, (2 + i) / 60, _f(), out)
    assert len(eng.transients) == 0


def test_color_stab_region_and_decay():
    out = np.zeros((MODEL.n, 3), np.float32)
    stab = ColorStab(MODEL, (1.0, 0.0, 0.0), gain=1.0, release=0.1, region="corners")

    class C:  # minimal ctx
        dt = 1 / 60
    stab.apply(C(), out)
    assert out[MODEL.corner_mask].sum() > 0.0
    assert out[MODEL.edge_mask].sum() == 0.0  # corners only
    for _ in range(60):
        stab.apply(C(), out)
    assert stab.done


def test_knob_param_changes_evolution_and_intensity():
    eng = VisualEngine(MODEL, n_buckets=8)
    presets.load("deep", eng)
    # find the speed knob and zero it -> hue should not advance
    for i, kb in enumerate(eng.knob_spec):
        if kb.effect == "speed":
            eng.knob_vals[i] = 0.0
    out = np.zeros((MODEL.n, 3), np.float32)
    t = 0.0
    for _ in range(60):
        t += 1 / 60
        eng.render(MODEL, t, _f(), out)
    assert eng._hue == 0.0  # speed=0 -> frozen drift


def test_mixer_routes_triggers_and_knobs_per_deck():
    mx = DeckMixer(MODEL, n_buckets=8)
    # each deck's pad column has its preset's trigger colours
    cells = mx.trigger_cells(1)
    assert len(cells) >= 1 and len(cells[0][1]) == 3
    # firing a deck adds a transient on that deck only
    label = mx.trigger_label(2, 0)
    mx.fire(2, label, 1.0)
    assert len(mx.decks[2].transients) == 1 and len(mx.decks[0].transients) == 0
    # knob set + reset
    mx.set_knob(0, 0, 0.9)
    assert mx.knob_vals(0)[0] == 0.9
    mx.reset_knobs(0)
    assert mx.knob_vals(0)[0] == mx.decks[0].knob_spec[0].default


def test_held_glow_sustains_then_releases():
    from cube_dance.visuals.engine.elements import HeldGlow

    g = HeldGlow(MODEL, (1.0, 1.0, 1.0), region="all", attack=0.04, release=0.1)

    class C:
        dt = 1 / 30

    out = np.zeros((MODEL.n, 3), np.float32)
    for _ in range(30):
        out[:] = 0.0
        g.apply(C(), out)
    assert out.max() > 0.5 and not g.done  # sustained while held
    g.release()
    for _ in range(90):
        out[:] = 0.0
        g.apply(C(), out)
    assert g.done  # fades out and finishes after release


def test_mixer_hold_trigger_flag_and_fire_returns_element():
    mx = DeckMixer(MODEL, n_buckets=8)  # decks default deep/punchy/minimal/strobe
    assert mx.trigger_hold(0, "swell") is True  # deep's swell is a hold trigger
    assert mx.trigger_hold(0, "comet") is False  # deep's comet is one-shot
    el = mx.fire(0, "swell", 1.0)
    assert el is not None and hasattr(el, "release")


def test_encoder_wraps_modulo_preset_count():
    from cube_dance.control import ControlState

    n = len(presets.PRESET_ORDER)
    s = ControlState()
    s.p_mod = n  # the app sets this to the preset count
    s.p = 0
    s.step_encoder(-1)
    assert s.p == n - 1  # scrolling down through 0 -> the LAST preset (not 9)
    s.step_encoder(1)
    assert s.p == 0  # and back up to the first


def test_blackout_kills_output():
    mx = DeckMixer(MODEL, n_buckets=8)
    mx.volumes = [0.9, 0, 0, 0]
    mx.update(MODEL, 0.0, _f())
    assert MODEL.colors.sum() > 0.0
    mx.vparams.blackout = True
    mx.update(MODEL, 1 / 60, _f())
    assert float(MODEL.colors.sum()) == 0.0
