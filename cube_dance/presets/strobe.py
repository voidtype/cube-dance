"""`strobe` preset — hard and percussive: whole-cube white kick flashes + dense
hat sparkle over a low-saturation spectrum. Mix in on drops.
"""

from __future__ import annotations

from ..visuals.engine.elements import HatSparkle, KickPulse, SpectrumBeams


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(SpectrumBeams(m, nb, sat=0.55))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=1.4, release=0.07))
    engine.add(HatSparkle(m, count=44, release=0.05))
