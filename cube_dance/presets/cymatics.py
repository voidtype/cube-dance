"""`cymatics` - Chladni standing-wave nodal pattern; pitch sets the node spacing."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("ripple", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("glint", (200, 255, 220), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("wipe", (160, 220, 255), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
]


def build(engine) -> None:
    engine.add(fx.Cymatics(engine.model))
