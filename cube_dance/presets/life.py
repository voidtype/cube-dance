"""`life` - a 3-D Game of Life cellular automaton evolving across the cube; kicks re-seed it."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("step", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("seed", (120, 255, 140), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("pulse", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("spark", (160, 255, 200), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.GameOfLife3D(m, hue=0.33))
