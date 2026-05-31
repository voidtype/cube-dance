"""Visual interface and the audio-feature struct passed to visuals.

A visual writes ``model.colors`` from the current features. Phase 1 features are
just a loudness ``level``; later phases extend this (bands, per-region levels,
beat phase, ...) without changing the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..led_topology import CubeModel


@dataclass
class Features:
    level: float = 0.0  # normalised overall loudness in [0, 1]
    bass: float = 0.0  # mono band energies in [0, 1]
    mid: float = 0.0
    treble: float = 0.0
    bass_l: float = 0.0  # per-channel bass (for left/right corner split)
    bass_r: float = 0.0


@runtime_checkable
class Visual(Protocol):
    def update(self, model: CubeModel, t: float, features: Features) -> None:
        """Write ``model.colors`` for time ``t`` and the given features."""
        ...
