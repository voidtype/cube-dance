"""`icosa` - a wireframe icosahedron of light rotating inside the cube."""

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
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("shock", (120, 255, 160), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("comet", (160, 255, 200), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("strobe", (200, 255, 220), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.PlatonicSolid(m, hue=0.33))
