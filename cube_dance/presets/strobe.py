"""`strobe` preset — hard and percussive: whole-cube white kick flashes + dense
hat sparkle over a low-saturation spectrum. Mix in on drops.

Pads (chaos): jagged lightning, a white strobe, multicolour confetti, a shockwave.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    Confetti, HatSparkle, KickPulse, Lightning, Shockwave, SpectrumBeams, StrobeBurst,
)

KNOBS = [
    Knob("blast", "intensity", 0.75),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.6),
    Knob("size", "space", 0.6),
]

TRIGGERS = [
    Trigger("bolt", (255, 255, 255), lambda m, s, c: Lightning(m, c, strikes=5, gain=1.7, dur=0.3)),
    Trigger("white", (200, 220, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.6, flashes=8, interval=0.05)),
    Trigger("confetti", (255, 80, 80), lambda m, s, c: Confetti(m, count=110, release=0.5)),
    Trigger("shock", (40, 120, 255), lambda m, s, c: Shockwave(m, c, dur=0.45, gain=1.6 * s)),
]


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(SpectrumBeams(m, nb, sat=0.55))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=1.4, release=0.07))
    engine.add(HatSparkle(m, count=44, release=0.05))
