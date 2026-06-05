"""`feedback` - MilkDrop-style spiralling colour with decaying echoes."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("warp", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("bloom", (255, 120, 220), lambda m, s, c: el.ColorStab(m,c,gain=s,release=0.6,region='corners')),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("comet", (160, 255, 220), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("conf", (220, 160, 255), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
]


def build(engine) -> None:
    engine.add(fx.Feedback(engine.model))
