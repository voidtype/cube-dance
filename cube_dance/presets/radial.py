"""`radial` - Monstercat-style radial spectrum wrapped around the cube."""

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
    Trigger("shock", (255, 120, 160), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("spark", (120, 255, 200), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("strobe", (200, 220, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
]


def build(engine) -> None:
    engine.add(fx.RadialSpectrum(engine.model))
