"""`deep` preset — smooth, evolving body with a slow sweep and gentle kicks.

Pads (smooth/cool): a long swell, a slow comet, a soft upward wipe, a corner bloom.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    AmbientWash, BassCorners, ColorStab, Comet, HatSparkle, KickPulse, Pulse,
    SpectrumBeams, Sweep, Wipe,
)

KNOBS = [
    Knob("bright", "intensity", 0.6),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.35),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("swell", (80, 150, 255), lambda m, s, c: ColorStab(m, c, gain=0.8 * s, release=0.9)),
    Trigger("comet", (120, 255, 220), lambda m, s, c: Comet(m, c, dur=1.3, turns=1.0, gain=1.1 * s)),
    Trigger("wipe", (150, 120, 255), lambda m, s, c: Wipe(m, c, axis=1, dur=1.0, gain=0.9 * s)),
    Trigger("bloom", (255, 170, 60), lambda m, s, c: ColorStab(m, c, gain=s, release=0.5, region="corners")),
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
