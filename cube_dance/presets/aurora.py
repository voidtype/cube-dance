"""`aurora` - vertical curtains of light (northern-lights) waving around the cube."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("sway", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("swell", (120, 255, 180), lambda m, s, c: el.HeldGlow(m, c, attack=0.25, release=0.6), hold=True),
    Trigger("shimmer", (180, 255, 220), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("wipe", (120, 255, 200), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
    Trigger("bloom", (200, 120, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.55, region='corners')),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.Aurora(m))
