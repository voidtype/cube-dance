"""Streaming feature processor: dynamic, auto-levelled features from spectrum windows.

Two adaptive mechanisms, both streaming (no precompute -> works for a file or a
live stream), with everything tunable via :class:`AgcParams` for the DSL:

1. **Per-bucket auto-level** -- each frequency bucket is normalised by its own
   slowly-decaying peak, so every band fills a useful range and *any* track gets a
   "nice mix" (a bass-heavy track still shows its treble, and vice-versa).
2. **Global presence gate** -- overall loudness, relative to a slower decaying
   reference, gates everything; with ``presence_gamma > 1`` a quiet *section*
   (quiet relative to the recent track level) **exponentially hides** while loud
   passages pop. Across whole tracks the references adapt, so quiet songs still
   show.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .analysis import SpectrumAnalyzer


@dataclass
class AgcParams:
    bucket_tau: float = 1.5      # s; per-bucket auto-level reference decay
    track_tau: float = 4.0       # s; overall loudness reference decay (presence)
    bucket_gate: float = 1e-4    # bucket-energy floor (avoid div-by-zero in silence)
    level_gate: float = 0.004    # RMS floor for presence
    gamma: float = 1.4           # per-bucket contrast (stark)
    presence_gamma: float = 2.0  # >1: quiet sections hide exponentially


class FeatureProcessor:
    def __init__(self, analyzer: SpectrumAnalyzer, params: AgcParams | None = None) -> None:
        self.an = analyzer
        self.p = params or AgcParams()
        nb = analyzer.n_buckets
        self.bpeak_l = np.full(nb, self.p.bucket_gate, dtype=np.float32)
        self.bpeak_r = np.full(nb, self.p.bucket_gate, dtype=np.float32)
        self.lvl_ref = self.p.level_gate

    def _autolevel(self, raw: np.ndarray, bpeak: np.ndarray, decay: float) -> np.ndarray:
        np.maximum(raw, bpeak * decay, out=bpeak)  # decaying per-bucket peak
        return np.clip(raw / np.maximum(bpeak, self.p.bucket_gate), 0.0, 1.0)

    def process(self, window_stereo: np.ndarray, dt: float):
        from ..visuals.base import Features  # local import: avoid import cycle

        raw_l, raw_r = self.an.analyze(window_stereo)
        b_decay = math.exp(-dt / self.p.bucket_tau) if dt > 0 else 1.0
        norm_l = self._autolevel(raw_l, self.bpeak_l, b_decay)
        norm_r = self._autolevel(raw_r, self.bpeak_r, b_decay)

        # Global presence: overall loudness vs a slower decaying reference.
        lvl_raw = float(np.sqrt(np.mean(window_stereo.astype(np.float32) ** 2)))
        t_decay = math.exp(-dt / self.p.track_tau) if dt > 0 else 1.0
        self.lvl_ref = max(lvl_raw, self.lvl_ref * t_decay)
        level = min(1.0, lvl_raw / max(self.lvl_ref, self.p.level_gate))
        presence = level**self.p.presence_gamma

        bl = (np.power(norm_l, self.p.gamma) * presence).astype(np.float32)
        br = (np.power(norm_r, self.p.gamma) * presence).astype(np.float32)

        nb = self.an.n_buckets
        nlow = max(1, nb // 3)
        mono = 0.5 * (bl + br)
        return Features(
            level=level,
            bass=float(mono[:nlow].max()),
            mid=float(mono[nlow:2 * nlow].max()) if 2 * nlow > nlow else 0.0,
            treble=float(mono[2 * nlow:].max()) if nb > 2 * nlow else 0.0,
            bass_l=float(bl[:nlow].max()),
            bass_r=float(br[:nlow].max()),
            buckets_l=bl,
            buckets_r=br,
        )
