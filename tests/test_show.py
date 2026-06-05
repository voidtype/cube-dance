"""DUSTLIGHT show director tests: the night progresses through its seven acts,
the new signature presets exist and render, and the crossfade is pop-free."""

from __future__ import annotations

import numpy as np
import pytest

from cube_dance import presets
from cube_dance.config import CubeConfig
from cube_dance.led_topology import build_model
from cube_dance.show import DUSTLIGHT, RaveShow, build_show
from cube_dance.visuals import Features
from cube_dance.visuals.engine.mixer import DeckMixer

MODEL = build_model(CubeConfig())


def _f(t: float = 0.0) -> Features:
    return Features(
        level=0.6 + 0.4 * np.sin(t * 3), bass=0.7, mid=0.5, treble=0.4, bass_l=0.7, bass_r=0.6,
        buckets_l=np.abs(np.sin(np.linspace(0, 3, 8) + t)).astype(np.float32),
        buckets_r=np.abs(np.cos(np.linspace(0, 3, 8) + t)).astype(np.float32),
    )


# --- The four new signature presets --------------------------------------------
def test_dustlight_presets_registered():
    for name in ("ember", "dust", "monolith", "sunrise"):
        assert name in presets.PRESET_ORDER


def test_dustlight_presets_render_and_declare_surface():
    from cube_dance.visuals.engine import VisualEngine
    from cube_dance.visuals.engine.element import Knob, Trigger

    for name in ("ember", "dust", "monolith", "sunrise"):
        eng = VisualEngine(MODEL, n_buckets=8)
        presets.load(name, eng)
        out = np.zeros((MODEL.n, 3), np.float32)
        t = 0.0
        for _ in range(30):
            t += 1 / 60
            eng.render(MODEL, t, _f(t), out)
        assert out.sum() > 0.0, name
        assert 1 <= len(eng.knob_spec) <= 4 and all(isinstance(k, Knob) for k in eng.knob_spec)
        assert 1 <= len(eng.triggers) <= 4 and all(isinstance(tr, Trigger) for tr in eng.triggers.values())


# --- Every preset the show references must exist -------------------------------
def test_all_referenced_presets_exist():
    referenced = {p for act in DUSTLIGHT for p in act.presets if p}
    missing = referenced - set(presets.PRESET_ORDER)
    assert not missing, missing


# --- The director runs the whole night -----------------------------------------
def test_show_progresses_through_all_seven_acts_in_order():
    mix = DeckMixer(MODEL, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    seen: list[str] = []
    t = 0.0
    while t < show.duration:
        act = show.apply(t)
        if not seen or seen[-1] != act.name:
            seen.append(act.name)
        t += 1 / 30
    assert seen == [a.name for a in DUSTLIGHT]


def test_show_loops():
    mix = DeckMixer(MODEL, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    # one full night later we are back in the opening act
    assert show.locate(0.0)[0] == 0
    assert show.act_at(70.0 + 0.5).name == DUSTLIGHT[0].name


def test_apply_keeps_volumes_and_master_in_range():
    mix = DeckMixer(MODEL, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    t = 0.0
    while t < show.duration:
        show.apply(t)
        assert all(0.0 <= v <= 1.0 for v in mix.volumes)
        assert 0.0 <= mix.vparams.master <= 1.0
        t += 0.3


# --- The shape of the night ----------------------------------------------------
def test_intensity_arc_quiet_arrival_loud_peak():
    by_name = {a.name: a for a in DUSTLIGHT}
    assert by_name["Peak"].intensity == max(a.intensity for a in DUSTLIGHT)
    assert by_name["Arrival"].intensity == min(a.intensity for a in DUSTLIGHT)
    assert by_name["Peak"].sync is True  # the rig pumps on kicks at peak
    # the arc rises into the peak then breathes back down before the dawn
    assert by_name["Arrival"].intensity < by_name["The Build"].intensity < by_name["Peak"].intensity
    assert by_name["Before Light"].intensity < by_name["Peak"].intensity


def test_rendered_brightness_peaks_at_peak():
    mix = DeckMixer(MODEL, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    seg = show.duration / show.n_acts
    bright: dict[str, float] = {}
    for ai, act in enumerate(DUSTLIGHT):
        t = seg * (ai + 0.7)  # sample late in each act (past the crossfade)
        show.apply(t)
        acc = 0.0
        for k in range(8):
            mix.update(MODEL, t + k / 60, _f(t + k / 60))
            acc += float(MODEL.colors.sum())
        bright[act.name] = acc
    assert bright["Peak"] == max(bright.values())
    assert bright["Arrival"] == min(bright.values())


# --- Pop-free crossfade --------------------------------------------------------
def test_preset_swap_fades_in_from_black():
    mix = DeckMixer(MODEL, n_buckets=8)
    show = RaveShow(mix, duration=70.0)
    seg = show.duration / show.n_acts
    # just into "Settling": deck 0 ember->deep, deck 1 dust->minimal (both swap)
    show.apply(seg + 1e-3)
    assert mix.volumes[0] < 0.02  # swapped deck enters from black (no pop)
    assert mix.volumes[1] < 0.02


# --- The factory ---------------------------------------------------------------
def test_build_show_aliases_and_unknown():
    mix = DeckMixer(MODEL, n_buckets=8)
    assert build_show(mix, "dustlight", 2).acts is DUSTLIGHT
    assert build_show(mix, "RAVE", 2).acts is DUSTLIGHT  # alias + case-insensitive
    assert build_show(mix, "dustlight", 4).duration == pytest.approx(240.0)
    with pytest.raises(ValueError):
        build_show(mix, "no-such-show", 2)
