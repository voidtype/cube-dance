"""`modal` - the truss rings: a structural vibration mode brightens with the bass."""

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
    Trigger("strike", (255, 140, 80), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("flash", (255, 200, 120), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("spark", (255, 230, 160), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("bolt", (255, 160, 60), lambda m, s, c: el.Lightning(m, c, strikes=5, gain=1.6)),
]


def build(engine) -> None:
    engine.add(fx.ModalResonance(engine.model))
