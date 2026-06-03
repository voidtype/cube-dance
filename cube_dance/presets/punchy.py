"""`punchy` preset — saturated, hard kicks flash the whole cube, fast chase.

Pads (hard): white slam, a blast shockwave, a coloured strobe, a riser.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    BassCorners, Chase, ColorStab, HatSparkle, KickPulse, Pulse, RiserSweep,
    Shockwave, SpectrumBeams, StrobeBurst,
)

KNOBS = [
    Knob("drive", "intensity", 0.7),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.5),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("slam", (255, 255, 255), lambda m, s, c: ColorStab(m, c, gain=1.2 * s, release=0.16)),
    Trigger("shock", (90, 200, 255), lambda m, s, c: Shockwave(m, c, dur=0.5, gain=1.6 * s)),
    Trigger("strobe", (255, 60, 160), lambda m, s, c: StrobeBurst(m, c, gain=1.4, flashes=6)),
    Trigger("riser", (255, 150, 30), lambda m, s, c: RiserSweep(m, c, dur=1.0, gain=1.1 * s)),
]


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(Pulse(m, hue=0.0, sat=0.85, base=0.04, gain=0.45, react="energy"))
    engine.add(SpectrumBeams(m, nb, sat=1.0))
    engine.add(BassCorners(m, hue=0.02, sat=1.0))
    engine.add(Chase(m, rate=0.5, width=0.07, hue=0.5, gain=0.7))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=1.2, release=0.12))
    engine.add(HatSparkle(m, count=32, release=0.07))
