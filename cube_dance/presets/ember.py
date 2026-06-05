"""`ember` - the Monolith at rest: a warm, low, slowly-breathing body (DUSTLIGHT arrival / morning)."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import elements as el

KNOBS = [
    Knob("warmth", "intensity", 0.45),
    Knob("colour", "hue", 0.0),
    Knob("drift", "speed", 0.15),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("swell", (255, 150, 60), lambda m, s, c: el.HeldGlow(m, c, attack=0.4, release=1.0), hold=True),
    Trigger("stab", (255, 120, 40), lambda m, s, c: el.ColorStab(m, c, gain=0.8 * s, release=0.6)),
    Trigger("bloom", (255, 90, 40), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.7, region="corners")),
    Trigger("spark", (255, 200, 120), lambda m, s, c: el.SparkBurst(m, c, count=20, release=0.8)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(el.Pulse(m, hue=0.04, sat=0.85, base=0.04, gain=0.3, react="bass"))
    engine.add(el.AmbientWash(m, base=0.04, sat=0.6))
    engine.add(el.BassCorners(m, hue=0.0, sat=0.95))
