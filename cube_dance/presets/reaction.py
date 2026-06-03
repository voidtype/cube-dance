"""`reaction` - Gray-Scott reaction-diffusion: organic spots and worms morphing over the cube."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("scale", "space", 0.5),
]

TRIGGERS = [
    Trigger("inject", (120, 255, 200), lambda m, s, c: el.HeldGlow(m, c, attack=0.25, release=0.6), hold=True),
    Trigger("ripple", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("stab", (255, 160, 80), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("spark", (200, 255, 160), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.ReactionDiffusion(m, hue=0.45))
