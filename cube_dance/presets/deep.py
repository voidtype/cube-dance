"""`deep` preset — smooth, evolving, with a slow vertical sweep and gentle kicks."""

from __future__ import annotations

from ..visuals.engine.elements import (
    AmbientWash, BassCorners, HatSparkle, KickPulse, SpectrumBeams, Sweep,
)


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(AmbientWash(m, base=0.04, sat=0.6))
    engine.add(SpectrumBeams(m, nb, sat=0.85))
    engine.add(BassCorners(m, hue=0.0, sat=0.95))
    engine.add(Sweep(m, axis=1, rate=0.11, width=0.13, hue=0.58, gain=0.45))
    engine.add(KickPulse(m, region="corners", sat=0.0, gain=0.9, release=0.20))
    engine.add(HatSparkle(m, count=18, release=0.10))
