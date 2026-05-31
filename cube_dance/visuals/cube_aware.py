"""Cube-aware visual: map frequency bands to cube regions.

Corners react to **bass**, split **left/right** by stereo channel (left-hand corners
follow the left channel's bass, right-hand corners the right). Beams (edges) react to
**mid/treble**. Each band is smoothed with a fast-attack / slow-release follower, and the
hues drift slowly over time for gentle evolution. This is the first spatially-aware visual;
Phase 4 makes the mapping configurable.
"""

from __future__ import annotations

import colorsys
import math

import numpy as np

from ..led_topology import CubeModel
from .base import Features


class CubeAwareVisual:
    def __init__(self, model: CubeModel, attack_s: float = 0.03, release_s: float = 0.22) -> None:
        x = model.positions[:, 0]
        self.corners_left = model.corner_mask & (x < 0)
        self.corners_right = model.corner_mask & (x >= 0)
        self.edges = model.edge_mask
        self.attack_s = attack_s
        self.release_s = release_s
        self._d = {"bass_l": 0.0, "bass_r": 0.0, "mid": 0.0, "treble": 0.0}
        self._last_t: float | None = None
        self._phase = 0.0

    def _follow(self, key: str, target: float, dt: float) -> float:
        cur = self._d[key]
        if dt <= 0.0:
            cur = target
        else:
            tau = self.attack_s if target > cur else self.release_s
            cur += (target - cur) * (1.0 - math.exp(-dt / max(tau, 1e-4)))
        self._d[key] = cur
        return cur

    def update(self, model: CubeModel, t: float, features: Features) -> None:
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t
        self._phase += dt

        bl = self._follow("bass_l", features.bass_l, dt)
        br = self._follow("bass_r", features.bass_r, dt)
        md = self._follow("mid", features.mid, dt)
        tr = self._follow("treble", features.treble, dt)

        warm = (0.02 + 0.04 * math.sin(self._phase * 0.07)) % 1.0  # red -> orange drift
        cool = (0.55 + 0.07 * math.sin(self._phase * 0.05)) % 1.0  # cyan -> blue drift
        col_l = np.array(colorsys.hsv_to_rgb(warm, 1.0, bl), dtype=np.float32)
        col_r = np.array(colorsys.hsv_to_rgb(warm, 1.0, br), dtype=np.float32)
        edge_b = min(1.0, 0.30 * md + 0.90 * tr)
        col_e = np.array(colorsys.hsv_to_rgb(cool, 0.85, edge_b), dtype=np.float32)

        c = model.colors
        c[:] = 0.0
        c[self.corners_left] = col_l
        c[self.corners_right] = col_r
        c[self.edges] = col_e
        np.clip(c, 0.0, 1.0, out=c)
