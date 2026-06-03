"""`sun` - a moving light orbits the cube; each LED shades by its normal, giving real 3-D depth."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("orbit", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 240, 200), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("bloom", (255, 200, 120), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.55, region='corners')),
    Trigger("shock", (255, 220, 160), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("hold", (255, 235, 190), lambda m, s, c: el.HeldGlow(m, c, attack=0.25, release=0.6), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.NormalSun(m, hue=0.12))
