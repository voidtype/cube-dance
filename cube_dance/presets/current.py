"""`current` - energy injected at points diffuses and decays along the edge frame like a current."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("flow", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("surge", (120, 220, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("arc", (160, 200, 255), lambda m, s, c: el.Lightning(m, c, strikes=5, gain=1.6)),
    Trigger("comet", (120, 255, 255), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("glint", (200, 240, 255), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.TrussCurrent(m, hue=0.55))
