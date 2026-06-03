"""`snake` - a light travels along the cube's edges leaving a fading trail (a Tron light-cycle)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("trail", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("arc", (120, 255, 180), lambda m, s, c: el.Lightning(m, c, strikes=5, gain=1.6)),
    Trigger("comet", (160, 255, 220), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("glint", (200, 255, 220), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.EdgeSnake(m, hue=0.33))
