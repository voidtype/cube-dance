"""Audio file decode + a normalised loudness envelope.

Loads a whole file into memory (DJ tracks are minutes -- trivial in RAM), keeps a
mono mix for analysis and the original channels for playback, and precomputes a
per-hop RMS envelope normalised to [0, 1] so a level can be read at any position.
"""

from __future__ import annotations

import os

import numpy as np

DEFAULT_HOP = 512


class AudioFile:
    def __init__(self, samples: np.ndarray, sr: int, hop: int = DEFAULT_HOP) -> None:
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = samples[:, None]
        self.samples = samples  # (n, channels) for playback
        self.channels = samples.shape[1]
        self.mono = samples.mean(axis=1).astype(np.float32)  # (n,) for analysis
        self.sr = int(sr)
        self.hop = int(hop)
        self.duration = len(self.mono) / self.sr if self.sr else 0.0
        self.hop_s = self.hop / self.sr if self.sr else 0.0
        self._build_envelope()

    @classmethod
    def load(cls, path: str, hop: int = DEFAULT_HOP) -> "AudioFile":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path!r}")
        import soundfile as sf

        try:
            data, sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception as exc:  # noqa: BLE001 - surface a clear message
            raise ValueError(f"Could not decode audio file {path!r}: {exc}") from exc
        return cls(data, sr, hop=hop)

    @classmethod
    def from_array(cls, data: np.ndarray, sr: int, hop: int = DEFAULT_HOP) -> "AudioFile":
        return cls(np.asarray(data, dtype=np.float32), sr, hop=hop)

    def _build_envelope(self) -> None:
        n = len(self.mono)
        if n == 0:
            self.envelope = np.zeros(1, dtype=np.float32)
            return
        hop = self.hop
        n_hops = int(np.ceil(n / hop))
        padded = np.pad(self.mono, (0, n_hops * hop - n))
        frames = padded.reshape(n_hops, hop)
        rms = np.sqrt(np.mean(frames * frames, axis=1))
        norm = max(float(np.percentile(rms, 99.0)), 1e-6)  # robust to lone transients
        self.envelope = np.clip(rms / norm, 0.0, 1.0).astype(np.float32)

    def level_at(self, t: float) -> float:
        """Normalised loudness in [0, 1] at position ``t`` seconds (clamped)."""
        t = min(max(t, 0.0), self.duration)
        idx = min(int(t / self.hop_s) if self.hop_s else 0, len(self.envelope) - 1)
        return float(self.envelope[idx])
