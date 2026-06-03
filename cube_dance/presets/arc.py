"""`arc` - hard lightning arcs crawl along contiguous runs of the cube's edges."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("rate", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("bolt", (255, 255, 255), lambda m, s, c: el.Lightning(m, c, strikes=5, gain=1.6)),
    Trigger("flash", (200, 220, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("confetti", (180, 200, 255), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.CornerLightning(m, hue=0.6))
