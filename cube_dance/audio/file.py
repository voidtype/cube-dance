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
        self._build_bands()

    # --- Frequency bands (bass/mid/treble) per channel + mono ---------------
    def _hop_rms(self, sig: np.ndarray) -> np.ndarray:
        hop = self.hop
        n = len(sig)
        if n == 0:
            return np.zeros(1, dtype=np.float32)
        n_hops = int(np.ceil(n / hop))
        padded = np.pad(sig, (0, n_hops * hop - n))
        return np.sqrt(np.mean(padded.reshape(n_hops, hop) ** 2, axis=1))

    def _bandpass(self, sig: np.ndarray, lo: float, hi: float, order: int = 4) -> np.ndarray:
        from scipy.signal import butter, sosfiltfilt

        nyq = self.sr / 2.0
        hi = min(hi, nyq * 0.99)
        lo = max(lo, 1.0)
        if lo >= hi or len(sig) <= 3 * (2 * order + 1):
            return np.zeros_like(sig)
        sos = butter(order, [lo, hi], btype="band", fs=self.sr, output="sos")
        return sosfiltfilt(sos, sig)

    @staticmethod
    def _norm(env: np.ndarray) -> np.ndarray:
        scale = max(float(np.percentile(env, 99.0)) if env.size else 1.0, 1e-6)
        return np.clip(env / scale, 0.0, 1.0).astype(np.float32)

    def _build_bands(self) -> None:
        bands = {"bass": (30.0, 200.0), "mid": (200.0, 2000.0), "treble": (2000.0, 16000.0)}
        left = self.samples[:, 0]
        right = self.samples[:, 1] if self.channels > 1 else left
        self._band_env: dict[str, np.ndarray] = {}
        for name, (lo, hi) in bands.items():
            rl = self._hop_rms(self._bandpass(left, lo, hi))
            rr = self._hop_rms(self._bandpass(right, lo, hi))
            self._band_env[f"{name}_l"] = self._norm(rl)
            self._band_env[f"{name}_r"] = self._norm(rr)
            self._band_env[name] = self._norm(0.5 * (rl + rr))

    def bands_at(self, t: float) -> dict[str, float]:
        """bass/mid/treble (mono) + bass_l/bass_r at position ``t`` (clamped)."""
        t = min(max(t, 0.0), self.duration)
        idx = min(int(t / self.hop_s) if self.hop_s else 0, len(self.envelope) - 1)
        e = self._band_env
        return {
            "bass": float(e["bass"][idx]),
            "mid": float(e["mid"][idx]),
            "treble": float(e["treble"][idx]),
            "bass_l": float(e["bass_l"][idx]),
            "bass_r": float(e["bass_r"][idx]),
        }

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
