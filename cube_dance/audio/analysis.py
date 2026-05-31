"""Streaming spectral analysis: log-spaced frequency buckets per channel.

This is **real-time / per-window**, not precomputed: each call analyses one short
window of recent audio (the last ``win`` samples up to the playhead). The exact
same path works for a file slice now and a live ring buffer later (Phase 6), and
there is no load-time precompute (so no startup lag).
"""

from __future__ import annotations

import numpy as np

DEFAULT_BUCKETS = 8
FMIN = 30.0
FMAX = 16000.0


def bucket_edges(n_buckets: int, sr: int, fmin: float = FMIN, fmax: float = FMAX) -> np.ndarray:
    hi = min(fmax, sr / 2.0 * 0.99)
    return np.logspace(np.log10(fmin), np.log10(hi), n_buckets + 1)


class SpectrumAnalyzer:
    """Computes per-channel frequency-bucket energy for one audio window."""

    def __init__(self, sr: int, n_buckets: int = DEFAULT_BUCKETS, win: int = 2048,
                 fmin: float = FMIN, fmax: float = FMAX) -> None:
        self.sr = sr
        self.n_buckets = n_buckets
        self.win = win
        self.window = np.hanning(win).astype(np.float32)
        self.edges = bucket_edges(n_buckets, sr, fmin, fmax)
        freqs = np.fft.rfftfreq(win, 1.0 / sr)
        bin_bucket = np.clip(np.digitize(freqs, self.edges) - 1, -1, n_buckets - 1)
        self._masks = [bin_bucket == b for b in range(n_buckets)]

    def _buckets(self, sig: np.ndarray) -> np.ndarray:
        mag = np.abs(np.fft.rfft(sig * self.window))
        out = np.zeros(self.n_buckets, dtype=np.float32)
        for b, m in enumerate(self._masks):
            if m.any():
                out[b] = mag[m].mean()
        return out

    def analyze(self, window_stereo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``window_stereo`` is ``(win, channels)``; returns ``(buckets_l, buckets_r)``."""
        left = window_stereo[:, 0]
        right = window_stereo[:, 1] if window_stereo.shape[1] > 1 else left
        return self._buckets(left), self._buckets(right)
