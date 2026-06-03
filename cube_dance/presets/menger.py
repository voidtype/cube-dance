"""`menger` - a Menger sponge (the recursive cube fractal) lit inside the cube, slowly drifting."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("drift", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 200, 120), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("shock", (255, 140, 60), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("wipe", (255, 180, 80), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
    Trigger("glint", (255, 230, 160), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.MengerSponge(m, hue=0.08))
