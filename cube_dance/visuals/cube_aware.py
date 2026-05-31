"""Cube-aware visual: dynamic, stereo, frequency-bucketed, evolving.

- **Corners = bass**, split left/right by channel (warm, slowly drifting hue).
- **Beams = the spectrum**: frequency runs *along* each beam (low->high), so each
  beam is a little spectrum analyser rather than a flat colour. Beams lateralise by
  stereo -- left-side beams follow the left channel's buckets, right-side beams the
  right, centre (X-running) beams the mono mix. So panned content shows on that side.
- Brightness comes from the AGC-levelled bucket energies (stark: quiet hides).
- Colours **evolve and accelerate** over a set (a global hue phase whose drift rate
  grows over time), per frequency.

Parameters live in :class:`VisualParams` for the upcoming DSL.
"""

from __future__ import annotations

import math

import numpy as np

from ..geometry import build_edges
from ..led_topology import CubeModel
from ..patterns import hsv_to_rgb
from .base import Features
from .params import VisualParams


class CubeAwareVisual:
    def __init__(self, model: CubeModel, n_buckets: int = 8, params: VisualParams | None = None) -> None:
        self.n_buckets = n_buckets
        self.p = params or VisualParams()

        x = model.positions[:, 0]
        self.corners_left = model.corner_mask & (x < 0)
        self.corners_right = model.corner_mask & (x >= 0)

        # Per edge: which side (0=left, 1=right, 2=centre) by the edge's X.
        side_by_edge = {}
        for e in build_edges():
            side_by_edge[e.index] = 2 if e.axis == 0 else (0 if e.fixed[0] < 0 else 1)

        self.edge_idx = np.where(model.edge_mask)[0]
        # Frequency runs along the beam via the along-edge parameter.
        self.bucket_idx = np.clip((model.param[self.edge_idx] * n_buckets).astype(int), 0, n_buckets - 1)
        self.side = np.array([side_by_edge[int(e)] for e in model.element_id[self.edge_idx]])
        self.hue_base = (self.bucket_idx / max(n_buckets, 1)) * self.p.hue_spread

        self._elapsed = 0.0
        self._phase = 0.0
        self._corner_phase = 0.0
        self._last_t: float | None = None

    def update(self, model: CubeModel, t: float, features: Features) -> None:
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t
        self._elapsed += dt
        # Hue drift accelerates over the set.
        rate = self.p.hue_drift_base * (1.0 + (self._elapsed / 60.0) * self.p.hue_accel_per_min)
        self._phase += rate * dt
        self._corner_phase += self.p.corner_hue_drift * dt

        nb = self.n_buckets
        bl = features.buckets_l if features.buckets_l is not None else np.zeros(nb, np.float32)
        br = features.buckets_r if features.buckets_r is not None else np.zeros(nb, np.float32)
        mono = 0.5 * (bl + br)

        colors = model.colors
        colors[:] = 0.0

        # --- Beams: frequency-along-beam, lateralised by stereo ---
        val = np.where(self.side == 0, bl[self.bucket_idx],
                       np.where(self.side == 1, br[self.bucket_idx], mono[self.bucket_idx]))
        if self.p.gamma != 1.0:
            val = np.power(val, self.p.gamma)
        val = self.p.floor + (1.0 - self.p.floor) * np.clip(val, 0.0, 1.0)
        hue = (self.hue_base + self._phase + self.p.hue_offset) % 1.0
        colors[self.edge_idx] = hsv_to_rgb(hue, float(self.p.beam_sat), val.astype(np.float32))

        # --- Corners: bass, split left/right (kept warm) ---
        warm = (self.p.corner_hue + self._corner_phase + self.p.hue_offset) % 1.0
        colors[self.corners_left] = hsv_to_rgb(warm, float(self.p.corner_sat), float(features.bass_l))
        colors[self.corners_right] = hsv_to_rgb(warm, float(self.p.corner_sat), float(features.bass_r))

        if self.p.master != 1.0:
            colors *= self.p.master
        np.clip(colors, 0.0, 1.0, out=colors)
