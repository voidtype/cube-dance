"""`bulb` - escape-time of the Mandelbulb sampled on the cube shell, slowly rotating."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("glow", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("spin", "speed", 0.3),
    Knob("scale", "space", 0.5),
]

TRIGGERS = [
    Trigger("dive", (120, 160, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("stab", (255, 120, 220), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("comet", (160, 255, 220), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("confetti", (220, 160, 255), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.Mandelbulb(m, hue=0.6))
