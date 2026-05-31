"""Map the F1 control state onto the visual / AGC parameters.

"Relevant params for now" -- knobs and faders drive continuous params, the P
display shifts the global hue, and REVERSE flips the colour-drift direction.
Phase 5 will formalise the full control + evolution roles (likely via the DSL).
"""

from __future__ import annotations

from .state import ControlState

# Human-readable role per knob / fader, surfaced on the panel.
KNOB_ROLES = ("hide quiet", "contrast", "hue spread", "response")
FADER_ROLES = ("master", "evolve", "accel", "floor")


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


class ControlMap:
    def apply(self, s: ControlState, vp, ap) -> None:
        # Knobs -> AGC / visual shaping.
        ap.presence_gamma = _lerp(0.8, 3.5, s.knobs[0])  # how hard quiet hides
        ap.gamma = _lerp(0.8, 3.0, s.knobs[1])  # per-bucket contrast (stark)
        vp.hue_spread = _lerp(0.1, 1.3, s.knobs[2])
        ap.bucket_tau = _lerp(0.3, 4.0, s.knobs[3])  # response (low = snappy)

        # Faders -> brightness + colour evolution.
        vp.master = _lerp(0.0, 1.4, s.faders[0])
        mag = _lerp(0.0, 0.08, s.faders[1])
        vp.hue_drift_base = -mag if s.buttons.get("REVERSE") else mag
        vp.hue_accel_per_min = _lerp(0.0, 3.0, s.faders[2])
        vp.floor = _lerp(0.0, 0.15, s.faders[3])

        # Browse encoder display -> global hue offset.
        vp.hue_offset = s.p / 100.0
