"""`deep` preset — smooth, evolving body with a slow sweep and gentle kicks.

Pads (per deck): a warm stab, a colour wash, a slow riser (build), and a soft
sparkle. Knobs: brightness / colour / evolve / width.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    AmbientWash, BassCorners, ColorStab, HatSparkle, KickPulse, Pulse,
    RiserSweep, SparkBurst, SpectrumBeams, Sweep,
)

KNOBS = [
    Knob("bright", "intensity", 0.6),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.35),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("stab", (255, 170, 60), lambda m, s, c: ColorStab(m, c, gain=s, release=0.35)),
    Trigger("wash", (80, 150, 255), lambda m, s, c: ColorStab(m, c, gain=0.7 * s, release=0.9)),
    Trigger("build", (255, 90, 40), lambda m, s, c: RiserSweep(m, c, dur=1.6, gain=0.9 * s)),
    Trigger("glis", (120, 255, 180), lambda m, s, c: SparkBurst(m, c, count=30, release=0.7)),
]


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(Pulse(m, hue=0.62, sat=0.6, base=0.05, gain=0.35, react="bass"))
    engine.add(AmbientWash(m, base=0.04, sat=0.6))
    engine.add(SpectrumBeams(m, nb, sat=0.85))
    engine.add(BassCorners(m, hue=0.0, sat=0.95))
    engine.add(Sweep(m, axis=1, rate=0.11, width=0.13, hue=0.58, gain=0.45))
    engine.add(KickPulse(m, region="corners", sat=0.0, gain=0.9, release=0.20))
    engine.add(HatSparkle(m, count=18, release=0.10))
