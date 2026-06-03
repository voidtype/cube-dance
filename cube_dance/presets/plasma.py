"""`plasma` — a smooth flowing oil-slick of colour over the whole cube. Continuous
and *not* beat-reactive: an interference field of sinusoids with the palette
slowly rotating. The 'scale' knob zooms the pattern, 'flow' rotates the hue.

Pads (liquid): a soft ripple, a corner bloom, a warp comet, a soft confetti.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import ColorStab, Comet, Confetti, PlasmaField, Pulse, Shockwave

KNOBS = [
    Knob("glow", "intensity", 0.6),
    Knob("flow", "speed", 0.5),
    Knob("scale", "space", 0.5),
    Knob("shift", "hue", 0.0),
]

TRIGGERS = [
    Trigger("ripple", (120, 200, 255), lambda m, s, c: Shockwave(m, c, dur=1.0, gain=1.0 * s, thickness=0.14)),
    Trigger("bloom", (255, 120, 220), lambda m, s, c: ColorStab(m, c, gain=s, release=0.6, region="corners")),
    Trigger("warp", (200, 255, 160), lambda m, s, c: Comet(m, c, dur=1.1, turns=1.0, gain=1.0 * s)),
    Trigger("confetti", (255, 255, 210), lambda m, s, c: Confetti(m, count=60, release=0.8)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(PlasmaField(m, sat=0.95, base=0.6))
    engine.add(Pulse(m, hue=0.5, sat=0.7, base=0.02, gain=0.18, react="energy"))
