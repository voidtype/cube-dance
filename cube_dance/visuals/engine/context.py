"""Per-frame context handed to every element, plus small modulators.

The engine builds a Context each frame (events, continuous features, beat phase,
evolution state, time) and passes it to each element's ``apply``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Context:
    model: object
    t: float
    dt: float
    features: object  # visuals.base.Features (level, bass, buckets, events, beat, ...)
    evo_hue: float = 0.0  # accelerating global hue offset
    energy: float = 0.0  # smoothed overall energy 0..1
    density: float = 0.0  # smoothed onset density

    def events(self, kind: str | None = None):
        evs = getattr(self.features, "events", None) or []
        return [e for e in evs if kind is None or e.kind == kind] if evs else []

    @property
    def beat(self) -> float:
        return float(getattr(self.features, "beat", 0.0) or 0.0)


class EnvFollower:
    """Fast-attack / slow-release envelope, triggered by event strength."""

    def __init__(self, release_s: float = 0.18) -> None:
        self.release_s = release_s
        self.v = 0.0

    def trigger(self, level: float) -> None:
        self.v = max(self.v, float(level))

    def step(self, dt: float) -> float:
        if dt > 0:
            self.v *= math.exp(-dt / max(self.release_s, 1e-4))
        return self.v


def lfo(shape: str, phase: float) -> float:
    """Unipolar [0,1] LFO. ``phase`` is in cycles."""
    p = phase % 1.0
    if shape == "sine":
        return 0.5 + 0.5 * math.sin(2 * math.pi * p)
    if shape == "tri":
        return 1.0 - abs(2.0 * p - 1.0)
    if shape == "saw":
        return 1.0 - p
    return p  # ramp
