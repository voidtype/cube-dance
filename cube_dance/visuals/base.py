"""Visual interface and the audio-feature struct passed to visuals.

A visual writes ``model.colors`` from the current features. Phase 1 features are
just a loudness ``level``; later phases extend this (bands, per-region levels,
beat phase, ...) without changing the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

import numpy as np

from ..led_topology import CubeModel


@dataclass
class Features:
    """Dynamic, auto-levelled audio features for a single frame (all in [0, 1])."""

    level: float = 0.0  # overall loudness
    bass: float = 0.0  # mono band aggregates
    mid: float = 0.0
    treble: float = 0.0
    bass_l: float = 0.0  # per-channel bass (left/right corner split)
    bass_r: float = 0.0
    buckets_l: Optional[np.ndarray] = None  # (n_buckets,) per-channel spectrum
    buckets_r: Optional[np.ndarray] = None
    events: Optional[list] = None  # classified onset Events this frame (kick/hat/snare/perc)
    beat: float = 0.0  # rough beat phase 0..1


@runtime_checkable
class Visual(Protocol):
    def update(self, model: CubeModel, t: float, features: Features) -> None:
        """Write ``model.colors`` for time ``t`` and the given features."""
        ...
