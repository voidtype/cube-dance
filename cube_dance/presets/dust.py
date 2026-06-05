"""`dust` - warm embers / fireflies drifting up through the cube (the bush at night)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import elements as el, effects2 as fx2

KNOBS = [
    Knob("glow", "intensity", 0.6),
    Knob("colour", "hue", 0.0),
    Knob("drift", "speed", 0.15),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("spark", (255, 200, 120), lambda m, s, c: el.SparkBurst(m, c, count=34, release=0.8)),
    Trigger("flare", (255, 150, 60), lambda m, s, c: el.RiserSweep(m, c, dur=1.4, gain=0.8 * s)),
    Trigger("flash", (255, 230, 180), lambda m, s, c: el.ColorStab(m, c, gain=0.7 * s, release=0.6)),
    Trigger("swell", (255, 170, 90), lambda m, s, c: el.HeldGlow(m, c, attack=0.4, release=0.9), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(el.AmbientWash(m, base=0.02, sat=0.5))
    engine.add(fx2.DriftMotes(m, hue=0.08, sat=0.8))
