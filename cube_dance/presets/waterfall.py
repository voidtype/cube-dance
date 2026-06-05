"""`waterfall` - a falling spectrogram: frequency bands scroll down the cube."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("scroll", "speed", 0.3),
    Knob("space", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("wipe", (120, 255, 180), lambda m, s, c: el.Wipe(m, c, axis=1, dur=0.9, gain=1.0*s)),
    Trigger("conf", (255, 200, 120), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
    Trigger("glint", (200, 255, 255), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    engine.add(fx.Spectrogram(engine.model))
