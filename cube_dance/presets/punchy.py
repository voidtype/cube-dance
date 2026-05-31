"""`punchy` preset — saturated, hard kicks flash the whole cube, fast chase."""

from __future__ import annotations

from ..visuals.engine.elements import (
    BassCorners, Chase, HatSparkle, KickPulse, SpectrumBeams,
)


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(SpectrumBeams(m, nb, sat=1.0))
    engine.add(BassCorners(m, hue=0.02, sat=1.0))
    engine.add(Chase(m, rate=0.5, width=0.07, hue=0.5, gain=0.7))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=1.2, release=0.12))
    engine.add(HatSparkle(m, count=32, release=0.07))
