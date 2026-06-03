"""`accretion` - particles spiral inward toward a moving sink and vanish (an accretion disk)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("spin", "speed", 0.3),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 200, 120), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("comet", (255, 160, 80), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("shock", (255, 120, 60), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("confetti", (255, 180, 120), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.Accretion(m, hue=0.05))
