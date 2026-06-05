"""`blinder` - festival white strobe + base-ring blinder, beat-synced."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("rate", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("white", (255, 255, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
    Trigger("slam", (255, 255, 255), lambda m, s, c: el.ColorStab(m,c,gain=1.3*s,release=0.14)),
    Trigger("bolt", (220, 230, 255), lambda m, s, c: el.Lightning(m, c, strikes=5, gain=1.6)),
    Trigger("hold", (255, 255, 255), lambda m, s, c: el.HeldGlow(m, c, attack=0.25, release=0.6), hold=True),
]


def build(engine) -> None:
    engine.add(fx.Blinder(engine.model))
