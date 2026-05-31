"""Audio file decode + windowed access (no precompute).

Analysis is streaming (see :mod:`cube_dance.audio.analysis` /
:mod:`cube_dance.audio.processor`): this class only decodes the file and hands
out the window of recent samples ending at a playback position -- the same
interface a live input ring buffer will provide in Phase 6. No load-time
spectral precompute, so loading is instant.
"""

from __future__ import annotations

import os

import numpy as np


class AudioFile:
    def __init__(self, samples: np.ndarray, sr: int) -> None:
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = samples[:, None]
        self.samples = samples  # (n, channels)
        self.channels = samples.shape[1]
        self.mono = samples.mean(axis=1).astype(np.float32)
        self.sr = int(sr)
        self.duration = len(self.samples) / self.sr if self.sr else 0.0

    @classmethod
    def load(cls, path: str) -> "AudioFile":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path!r}")
        import soundfile as sf

        try:
            data, sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not decode audio file {path!r}: {exc}") from exc
        return cls(data, sr)

    @classmethod
    def from_array(cls, data: np.ndarray, sr: int) -> "AudioFile":
        return cls(np.asarray(data, dtype=np.float32), sr)

    def window_at(self, t: float, win: int) -> np.ndarray:
        """The ``(win, channels)`` block of samples ending at position ``t`` (s).

        Front-padded with zeros near the start. This mirrors a live ring buffer.
        """
        if len(self.samples) == 0 or self.sr == 0:
            return np.zeros((win, self.channels), dtype=np.float32)
        end = int(round(min(max(t, 0.0), self.duration) * self.sr))
        end = min(end, len(self.samples))
        start = end - win
        if start < 0:
            out = np.zeros((win, self.channels), dtype=np.float32)
            seg = self.samples[0:end]
            out[win - seg.shape[0]:] = seg
            return out
        return self.samples[start:end].astype(np.float32)

    def level_at(self, t: float, win: int = 2048) -> float:
        """Raw RMS of the mono window ending at ``t`` (clamped to [0, 1])."""
        w = self.window_at(t, win)
        return float(min(1.0, np.sqrt(np.mean(w.mean(axis=1) ** 2))))
