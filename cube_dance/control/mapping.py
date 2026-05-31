"""Map the F1 control state onto the visual / AGC parameters (Phase 5).

The **faders** are per-deck volumes (read directly by the deck mixer) and the
**browse encoder** selects the focused deck's preset (handled by the app), so
neither is mapped here. The **knobs** become global modulators every deck honors,
and a few **buttons** toggle global looks.
"""

from __future__ import annotations

from .state import ControlState

# Human-readable role per knob / fader, surfaced on the panel.
KNOB_ROLES = ("intensity", "evolve", "size", "hide quiet")
FADER_ROLES = ("deck 1", "deck 2", "deck 3", "deck 4")  # volumes (preset names shown live)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


class ControlMap:
    def apply(self, s: ControlState, vp, ap) -> None:
        # Knobs -> global modulators (affect every deck via the shared params).
        vp.intensity = _lerp(0.3, 1.7, s.knobs[0])  # overall brightness / gain

        evo = _lerp(0.0, 0.05, s.knobs[1])  # colour-evolution speed
        vp.hue_drift_base = -evo if s.buttons.get("REVERSE") else evo
        vp.hue_accel_per_min = _lerp(0.0, 3.0, s.knobs[1])

        size = _lerp(0.5, 1.8, s.knobs[2])
        vp.size = size * 1.5 if s.buttons.get("SIZE") else size

        if ap is not None:
            ap.presence_gamma = _lerp(0.8, 3.5, s.knobs[3])  # how hard quiet hides

        # Button looks.
        vp.freeze = bool(s.buttons.get("SHIFT"))  # hold the palette
        vp.mono = bool(s.buttons.get("TYPE"))  # stark / desaturated
