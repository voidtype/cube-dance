"""VU-meter visual: map loudness to a vertical fill of the cube.

The displayed level is an envelope follower (fast attack, slow release) over the
input level. Pixels below the displayed level (by normalised height, floor->top)
light on a green->amber->red ramp scaled by loudness; a thin peak-hold band marks
the highest recent level. All vectorised over the pixel array.
"""

from __future__ import annotations

import math

import numpy as np

from ..led_topology import CubeModel
from .base import Features

_GREEN = np.array([0.1, 1.0, 0.1])
_AMBER = np.array([1.0, 0.65, 0.0])
_RED = np.array([1.0, 0.1, 0.05])


def _height_ramp(h: np.ndarray) -> np.ndarray:
    """green (low) -> amber (mid) -> red (high), per normalised height h in [0,1]."""
    h = h[:, None]
    lower = _GREEN[None, :] + (_AMBER - _GREEN)[None, :] * (h / 0.5)
    upper = _AMBER[None, :] + (_RED - _AMBER)[None, :] * ((h - 0.5) / 0.5)
    return np.where(h < 0.5, lower, upper).astype(np.float32)


class VuMeter:
    def __init__(
        self,
        model: CubeModel,
        attack_s: float = 0.02,
        release_s: float = 0.30,
        peak_release_per_s: float = 0.6,
        peak_band: float = 0.02,
    ) -> None:
        self.attack_s = attack_s
        self.release_s = release_s
        self.peak_release_per_s = peak_release_per_s
        self.peak_band = peak_band

        # Normalised height of each pixel (0 at floor, 1 at top) + colour ramp.
        h = (model.positions[:, 1] + model.cfg.half) / model.cfg.side_m
        self.height = np.clip(h, 0.0, 1.0).astype(np.float32)
        self.ramp = _height_ramp(self.height)

        self.disp = 0.0  # displayed (smoothed) level
        self.peak = 0.0
        self._last_t: float | None = None

    def update(self, model: CubeModel, t: float, features: Features) -> None:
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t

        level = float(np.clip(features.level, 0.0, 1.0))
        if dt <= 0.0:
            coeff = 1.0  # first frame / paused: settle immediately
        else:
            tau = self.attack_s if level > self.disp else self.release_s
            coeff = 1.0 - math.exp(-dt / max(tau, 1e-4))
        self.disp += (level - self.disp) * coeff

        # Peak hold with slow decay.
        self.peak = max(self.disp, self.peak - self.peak_release_per_s * dt)

        colors = model.colors
        colors[:] = 0.0
        # Fill from the floor up to the displayed level; brightness tracks level
        # so silence is dark and loud is bright.
        lit = self.height <= self.disp
        colors[lit] = self.ramp[lit] * self.disp

        # Peak-hold cap (a thin bright band), suppressed at silence.
        if self.peak > 0.05:
            band = np.abs(self.height - self.peak) <= self.peak_band
            colors[band] = (1.0, 1.0, 1.0)
        np.clip(colors, 0.0, 1.0, out=colors)
