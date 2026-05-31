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
    level: float = 0.0  # normalised loudness in [0, 1]


@runtime_checkable
class Visual(Protocol):
    def update(self, model: CubeModel, t: float, features: Features) -> None:
        """Write ``model.colors`` for time ``t`` and the given features."""
        ...
