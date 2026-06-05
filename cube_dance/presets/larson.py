"""`larson` - the Knight Rider / Cylon sweeping bar with a fading tail."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects2 as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.72),
    Knob("colour", "hue", 0.0),
    Knob("speed", "speed", 0.3),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 40, 40), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("strobe", (255, 255, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.05), hold=True),
    Trigger("shock", (255, 80, 80), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4*s)),
    Trigger("spark", (255, 160, 120), lambda m, s, c: el.SparkBurst(m, c, count=30, release=0.6)),
]


def build(engine) -> None:
    engine.add(fx.LarsonScanner(engine.model))
