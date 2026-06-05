"""`barberpole` - stripes wind along and around each beam (the chord rows)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("coils", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("comet", (255, 160, 80), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("glint", (200, 255, 220), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    engine.add(fx.BarberPole(engine.model))
