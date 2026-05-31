"""Phase 5: 4-deck preset mixer, global modulators, F1 deck focus."""

from __future__ import annotations

import numpy as np
import pytest

from cube_dance import presets
from cube_dance.audio.events import Event
from cube_dance.config import CubeConfig
from cube_dance.control import ControlState
from cube_dance.led_topology import build_model
from cube_dance.visuals import Features
from cube_dance.visuals.engine import VisualEngine
from cube_dance.visuals.engine.context import Context
from cube_dance.visuals.engine.elements import HatSparkle
from cube_dance.visuals.engine.mixer import DeckMixer
from cube_dance.visuals.params import VisualParams

MODEL = build_model(CubeConfig())


def _f(level: float = 0.8) -> Features:
    return Features(level=level, bass_l=0.7, bass_r=0.6,
                    buckets_l=np.ones(8, np.float32), buckets_r=np.ones(8, np.float32))


# --- Deck mixer --------------------------------------------------------------

def test_mixer_defaults_to_distinct_presets():
    mx = DeckMixer(MODEL, n_buckets=8)
    assert mx.preset_name == ["deep", "punchy", "minimal", "strobe"]
    assert all(len(d.elements) > 0 for d in mx.decks)


def test_mixer_blends_by_volume():
    f = _f()
    a = DeckMixer(MODEL, n_buckets=8)
    a.volumes = [1.0, 0.0, 0.0, 0.0]
    a.update(MODEL, 0.0, f)  # first frame: dt=0 -> deterministic (no evolution)
    full = MODEL.colors.copy()

    b = DeckMixer(MODEL, n_buckets=8)
    b.volumes = [0.4, 0.0, 0.0, 0.0]
    b.update(MODEL, 0.0, f)
    part = MODEL.colors.copy()

    assert full.sum() > 0.0
    assert 0.0 < part.sum() < full.sum()  # volume scales the deck's contribution

    z = DeckMixer(MODEL, n_buckets=8)
    z.volumes = [0.0, 0.0, 0.0, 0.0]
    z.update(MODEL, 0.0, f)
    assert float(MODEL.colors.sum()) == 0.0  # all muted -> dark


def test_set_deck_preset_swaps_elements():
    mx = DeckMixer(MODEL, n_buckets=8)
    mx.set_deck_preset(0, "strobe")
    assert mx.preset_name[0] == "strobe"
    assert mx.preset_index[0] == presets.PRESET_ORDER.index("strobe")
    assert len(mx.decks[0].elements) > 0


def test_preset_order_has_the_builtins():
    for name in ("deep", "punchy", "minimal", "strobe"):
        assert name in presets.PRESET_ORDER


# --- Global modulators -------------------------------------------------------

def _render(vparams: VisualParams, preset: str = "deep") -> np.ndarray:
    eng = VisualEngine(MODEL, n_buckets=8, vparams=vparams)
    presets.load(preset, eng)
    out = np.zeros((MODEL.n, 3), np.float32)
    eng.render(MODEL, 0.0, _f(), out)  # dt=0: intensity applied, no evolution/clip
    return out


def _render_intensity(k: float) -> np.ndarray:
    eng = VisualEngine(MODEL, n_buckets=8, vparams=VisualParams())
    presets.load("deep", eng)
    for i, kb in enumerate(eng.knob_spec):
        if kb.effect == "intensity":
            eng.knob_vals[i] = k
    out = np.zeros((MODEL.n, 3), np.float32)
    eng.render(MODEL, 0.0, _f(), out)
    return out


def test_intensity_knob_scales_brightness():
    lo = _render_intensity(0.1)
    hi = _render_intensity(0.9)
    assert lo.sum() > 0.0 and hi.sum() > 1.8 * lo.sum()  # brighter with the intensity knob


def test_mono_desaturates_to_white():
    color = _render(VisualParams(mono=False))
    mono = _render(VisualParams(mono=True))
    lit = mono.sum(axis=1) > 0.05
    assert lit.any()
    chroma_mono = float((mono[lit].max(axis=1) - mono[lit].min(axis=1)).mean())
    chroma_color = float((color[lit].max(axis=1) - color[lit].min(axis=1)).mean())
    assert chroma_mono < 1e-5 < chroma_color  # mono is greyscale, colour is not


def test_freeze_holds_the_hue():
    eng = VisualEngine(MODEL, n_buckets=8, vparams=VisualParams(hue_drift_base=0.1))
    presets.load("deep", eng)
    out = np.zeros((MODEL.n, 3), np.float32)
    t = 0.0
    for _ in range(60):
        t += 1 / 60
        eng.render(MODEL, t, _f(1.0), out)
    moved = eng._hue
    assert moved > 0.0  # evolving while not frozen
    eng.vparams.freeze = True
    for _ in range(60):
        t += 1 / 60
        eng.render(MODEL, t, _f(1.0), out)
    assert eng._hue == moved  # frozen: hue stops advancing


def test_size_scales_sparkle_count():
    big = HatSparkle(MODEL, count=10, seed=3)
    small = HatSparkle(MODEL, count=10, seed=3)
    out = np.zeros((MODEL.n, 3), np.float32)
    ev = [Event("hat", 1.0)]
    big.apply(Context(model=MODEL, t=0, dt=1 / 60, features=Features(events=ev), size=2.0), out)
    small.apply(Context(model=MODEL, t=0, dt=1 / 60, features=Features(events=ev), size=0.5), out)
    assert int((big.spark > 0.01).sum()) > int((small.spark > 0.01).sum())


# --- Deck focus (virtual F1) -------------------------------------------------

def test_virtual_f1_fader_touch_sets_focus():
    try:
        import moderngl as mgl

        ctx = mgl.create_standalone_context(require=330)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"no GL context: {exc}")
    try:
        from cube_dance.render.virtual_f1 import VirtualF1

        f1 = VirtualF1(ctx)
        f1.set_screen(1280, 800)
        st = ControlState()
        x0, y0, _, _ = f1._rect
        sc = f1._scale
        cx, top, bot, _hw = f1.faders[2]
        f1.on_press(x0 + cx * sc, y0 + (top + bot) / 2 * sc, st)
        assert st.focus_deck == 2  # touching fader 3 focuses deck 3
    finally:
        ctx.release()
