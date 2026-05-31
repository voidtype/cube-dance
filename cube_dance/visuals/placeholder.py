"""The Phase 0 placeholder pattern, wrapped as a Visual (no-audio fallback)."""

from __future__ import annotations

from ..led_topology import CubeModel
from ..patterns import PlaceholderPattern
from .base import Features


class PlaceholderVisual:
    def __init__(self) -> None:
        self._pattern = PlaceholderPattern()

    def update(self, model: CubeModel, t: float, features: Features) -> None:
        self._pattern.apply(model, t)
