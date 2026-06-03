"""`slice` - a flat plane sweeps and rotates through the cube, revealing its cross-section."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("wipe", (120, 220, 255), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("strobe", (200, 220, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.SlicePlane(m, hue=0.5))
