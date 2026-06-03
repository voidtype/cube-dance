"""`ripple` - expanding interfering wave shells from impact points, like water caustics."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("drop", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("ripple", (160, 220, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("spark", (200, 240, 255), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("comet", (120, 255, 255), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.RippleTank(m, hue=0.55))
