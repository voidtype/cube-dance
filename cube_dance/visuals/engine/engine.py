"""The visual engine: composites elements and evolves over time from the music."""

from __future__ import annotations

import math

import numpy as np

from ..params import VisualParams
from .context import Context


class VisualEngine:
    """A `Visual` (``update(model, t, features)``) that runs composable elements.

    Tracks a smoothed energy + onset density (composition awareness) and advances
    an accelerating global hue (evolution), then builds a Context and composites
    every element into ``model.colors``.
    """

    def __init__(self, model, n_buckets: int = 8, vparams: VisualParams | None = None) -> None:
        self.model = model
        self.n_buckets = n_buckets
        self.vparams = vparams or VisualParams()
        self.elements: list = []
        self._last_t: float | None = None
        self._energy = 0.0
        self._density = 0.0
        self._hue = 0.0
        self._elapsed = 0.0

    def add(self, element):
        self.elements.append(element)
        return element

    def render(self, model, t: float, features, out: np.ndarray) -> None:
        """Composite the elements into ``out`` (caller owns master + clipping).

        Advances this engine's evolution (honoring ``freeze``), builds the
        per-frame Context with the global modulators, clears ``out`` and blends
        every element, then applies the global ``intensity`` gain.
        """
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t
        self._elapsed += dt

        level = float(getattr(features, "level", 0.0) or 0.0)
        n_events = len(getattr(features, "events", None) or [])
        if dt > 0:
            self._energy += (level - self._energy) * (1.0 - math.exp(-dt / 0.6))
            self._density += ((n_events / dt) - self._density) * (1.0 - math.exp(-dt / 1.0))

        # Evolution: hue drift accelerates over the set and speeds up with energy.
        if dt > 0 and not self.vparams.freeze:
            rate = (self.vparams.hue_drift_base
                    * (1.0 + (self._elapsed / 60.0) * self.vparams.hue_accel_per_min)
                    * (0.5 + self._energy))
            self._hue = (self._hue + rate * dt) % 1.0
        evo_hue = (self._hue + self.vparams.hue_offset) % 1.0

        ctx = Context(model=model, t=t, dt=dt, features=features,
                      evo_hue=evo_hue, energy=min(1.0, self._energy * 1.3), density=self._density,
                      size=self.vparams.size, mono=self.vparams.mono)

        out[:] = 0.0
        for el in self.elements:
            el.apply(ctx, out)
        if self.vparams.intensity != 1.0:
            out *= self.vparams.intensity

    def update(self, model, t: float, features) -> None:
        """Standalone path: render into the model buffer, apply master, clip."""
        out = model.colors
        self.render(model, t, features, out)
        if self.vparams.master != 1.0:
            out *= self.vparams.master
        np.clip(out, 0.0, 1.0, out=out)
