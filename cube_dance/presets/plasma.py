"""`plasma` — a smooth flowing oil-slick of colour over the whole cube. Continuous
and *not* beat-reactive: an interference field of sinusoids with the palette
slowly rotating. The 'scale' knob zooms the pattern, 'flow' rotates the hue.
Hypnotic and liquid — deliberately unlike the percussive presets.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import ColorStab, PlasmaField, Pulse, RiserSweep, SparkBurst

KNOBS = [
    Knob("glow", "intensity", 0.6),
    Knob("flow", "speed", 0.5),
    Knob("scale", "space", 0.5),
    Knob("shift", "hue", 0.5),
]

TRIGGERS = [
    Trigger("ripple", (120, 200, 255), lambda m, s, c: ColorStab(m, c, gain=0.8 * s, release=0.7)),
    Trigger("bloom", (255, 120, 220), lambda m, s, c: ColorStab(m, c, gain=s, release=0.6, region="corners")),
    Trigger("warp", (200, 255, 160), lambda m, s, c: RiserSweep(m, c, dur=1.5, gain=0.8 * s)),
    Trigger("glint", (255, 255, 210), lambda m, s, c: SparkBurst(m, c, count=22, release=0.8)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(PlasmaField(m, sat=0.95, base=0.6))
    engine.add(Pulse(m, hue=0.5, sat=0.7, base=0.02, gain=0.18, react="energy"))
