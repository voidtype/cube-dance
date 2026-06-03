"""`lacing` - lights the eight corner clusters (the truss triangle detail) by spectrum and a chase."""

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
    Trigger("flash", (255, 200, 120), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.55, region='corners')),
    Trigger("shock", (255, 160, 80), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("spark", (255, 230, 160), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("strobe", (255, 255, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.TriangleLacing(m, hue=0.1))
