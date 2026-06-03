"""`minimal` preset — calm: spectrum beams + bass corners, no flashes or sweeps.

Pads (sparse/clean): a soft accent, a thin ring, a small glint, a slow wipe.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    AmbientWash, BassCorners, ColorStab, SparkBurst, Shockwave, SpectrumBeams, Wipe,
)

KNOBS = [
    Knob("level", "intensity", 0.55),
    Knob("colour", "hue", 0.5),
    Knob("drift", "speed", 0.25),
    Knob("width", "space", 0.5),
]

TRIGGERS = [
    Trigger("accent", (120, 200, 255), lambda m, s, c: ColorStab(m, c, gain=0.8 * s, release=0.4)),
    Trigger("ring", (255, 140, 60), lambda m, s, c: Shockwave(m, c, dur=0.9, gain=0.9 * s, thickness=0.07)),
    Trigger("glint", (150, 255, 200), lambda m, s, c: SparkBurst(m, c, count=18, release=0.6)),
    Trigger("wipe", (90, 120, 255), lambda m, s, c: Wipe(m, c, axis=0, dur=1.1, gain=0.7 * s, width=0.08)),
]


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(AmbientWash(m, base=0.03, sat=0.5))
    engine.add(SpectrumBeams(m, nb, sat=0.7))
    engine.add(BassCorners(m, hue=0.0, sat=0.85))
