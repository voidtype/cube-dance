"""`crystal` - diffusion-limited aggregation: a dendritic fractal slowly grows in 3-D."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("grow", "speed", 0.3),
    Knob("scale", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("glint", (200, 255, 255), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
    Trigger("wipe", (160, 200, 255), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(fx.DLA(m, hue=0.6))
