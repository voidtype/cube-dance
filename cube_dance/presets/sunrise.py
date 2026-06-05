"""`sunrise` - a dawn gradient that rises from the horizon (gold -> rose -> indigo) and blooms (DUSTLIGHT finale)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import elements as el, effects2 as fx2

KNOBS = [
    Knob("light", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("dawn", "speed", 0.3),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("bloom", (255, 180, 80), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.7, region="corners")),
    Trigger("flare", (255, 140, 60), lambda m, s, c: el.RiserSweep(m, c, dur=1.6, gain=0.9 * s)),
    Trigger("swell", (255, 200, 120), lambda m, s, c: el.HeldGlow(m, c, attack=0.5, release=1.2), hold=True),
    Trigger("glint", (255, 240, 200), lambda m, s, c: el.SparkBurst(m, c, count=24, release=0.8)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx2.Sunrise(m, sat=0.85))
    engine.add(el.Pulse(m, hue=0.06, sat=0.8, base=0.03, gain=0.3, react="energy"))
