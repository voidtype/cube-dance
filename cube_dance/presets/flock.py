"""`flock` - a murmuration of boids flying in 3-D; the cube glows where the swarm passes."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("spread", "space", 0.5),
]

TRIGGERS = [
    Trigger("scatter", (255, 120, 200), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
    Trigger("comet", (120, 255, 255), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3*s)),
    Trigger("stab", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("strobe", (120, 180, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.Boids(m, hue=0.55))
