"""`strobe` preset — hard and percussive: whole-cube white kick flashes + dense
hat sparkle over a low-saturation spectrum. Mix in on drops.

Pads are all about impact: white burst, coloured strobe, beam strobe, big riser.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    ColorStab, HatSparkle, KickPulse, RiserSweep, SpectrumBeams, StrobeBurst,
)

KNOBS = [
    Knob("blast", "intensity", 0.75),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.6),
    Knob("size", "space", 0.6),
]

TRIGGERS = [
    Trigger("white", (255, 255, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.6, flashes=8, interval=0.05)),
    Trigger("blast", (255, 40, 40), lambda m, s, c: ColorStab(m, c, gain=1.4 * s, release=0.12)),
    Trigger("beams", (40, 120, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.4, flashes=6, region="beams")),
    Trigger("riser", (255, 120, 0), lambda m, s, c: RiserSweep(m, c, dur=0.9, gain=1.3 * s)),
]


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(SpectrumBeams(m, nb, sat=0.55))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=1.4, release=0.07))
    engine.add(HatSparkle(m, count=44, release=0.05))
