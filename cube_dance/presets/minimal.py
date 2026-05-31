"""`minimal` preset — calm: spectrum beams + bass corners, no flashes or sweeps.

A clean layer to mix under busier decks (it stays out of the way).
"""

from __future__ import annotations

from ..visuals.engine.elements import AmbientWash, BassCorners, SpectrumBeams


def build(engine) -> None:
    m, nb = engine.model, engine.n_buckets
    engine.add(AmbientWash(m, base=0.03, sat=0.5))
    engine.add(SpectrumBeams(m, nb, sat=0.7))
    engine.add(BassCorners(m, hue=0.0, sat=0.85))
