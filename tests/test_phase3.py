"""Phase 3: control state, mapping, and virtual F1 interaction."""

from __future__ import annotations

import pytest

from cube_dance.audio.processor import AgcParams
from cube_dance.control import ControlMap, ControlState
from cube_dance.visuals.params import VisualParams


def test_control_state_encoder_and_toggle():
    s = ControlState()
    s.p = 98
    s.step_encoder(3)
    assert s.p == 1  # wraps mod 100
    s.step_encoder(-2)
    assert s.p == 99
    assert not s.buttons["SYNC"]
    s.toggle("SYNC")
    assert s.buttons["SYNC"]
    s.toggle("SYNC")
    assert not s.buttons["SYNC"]


def test_mapping_buttons_to_global_flags():
    # Phase 5: faders=deck volume, knobs=deck params, pads=triggers, encoder=preset
    # (routed by the app). ControlMap only turns the function buttons into vp flags.
    s, m, vp = ControlState(), ControlMap(), VisualParams()
    pairs = [("TYPE", "mono"), ("SHIFT", "freeze"), ("REVERSE", "reverse"),
             ("SIZE", "size_boost"), ("SYNC", "sync_pulse"), ("CAPTURE", "blackout")]
    for name, _ in pairs:
        s.buttons[name] = True
    m.apply(s, vp)
    assert all(getattr(vp, attr) for _, attr in pairs)
    for name, _ in pairs:
        s.buttons[name] = False
    m.apply(s, vp)
    assert not any(getattr(vp, attr) for _, attr in pairs)


def test_virtual_f1_interaction():
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
        x0, y0, w, h = f1._rect
        sc = f1._scale

        # Drag a knob up -> value increases.
        cx, cy, r = f1.knobs[0]
        sx, sy = x0 + cx * sc, y0 + cy * sc
        v0 = st.knobs[0]
        f1.on_press(sx, sy, st)
        f1.on_drag(sx, sy - 60, st)
        f1.on_release()
        assert st.knobs[0] > v0

        # Click a button -> toggles on.
        bx0, by0, bx1, by1 = f1.buttons["SYNC"]
        f1.on_press(x0 + (bx0 + bx1) / 2 * sc, y0 + (by0 + by1) / 2 * sc, st)
        assert st.buttons["SYNC"]

        # Scroll over the encoder -> P changes.
        ecx, ecy, er = f1.encoder
        p0 = st.p
        f1.on_scroll(x0 + ecx * sc, y0 + ecy * sc, 1, st)
        assert st.p == (p0 + 1) % 100

        # Clicking a pad queues a (col, row) trigger and lights that pad.
        px0, py0, px1, py1 = f1.pads_rect
        cx = px0 + (px1 - px0) / 8  # centre of column 0, row 0
        cy = py0 + (py1 - py0) / 8
        f1.on_press(x0 + cx * sc, y0 + cy * sc, st)
        assert st.pad_queue and st.pad_queue[-1] == (0, 0) and st.pad_glow[0] == 1.0
    finally:
        ctx.release()
