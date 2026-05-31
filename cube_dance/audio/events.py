"""Streaming drum/onset event detection (heuristic, low-latency).

Per analysis window: per-band **spectral flux** -> onset detection (moving-average
threshold + per-band refractory) -> **classify** each onset into kick/snare/hat/perc
from simple features (onset band frequency + spectral flatness). Sustained bass is
*not* handled here -- it is the continuous AGC'd `bass` from the FeatureProcessor;
because flux only spikes on transients, a sustained bass tone produces no kick events
while a sharp kick does, which is exactly the kick-vs-bass split. A rough tempo/phase
is tracked from onset intervals. No precompute; same path works for live audio.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

KINDS = ("kick", "snare", "hat", "perc")


@dataclass
class Event:
    kind: str
    strength: float  # ~0..1


class EventDetector:
    def __init__(self, sr: int, win: int = 1024, n_bands: int = 6,
                 fmin: float = 30.0, fmax: float = 18000.0, threshold: float = 1.8) -> None:
        self.sr = sr
        self.win = win
        self.threshold = threshold
        self.window = np.hanning(win).astype(np.float32)
        freqs = np.fft.rfftfreq(win, 1.0 / sr)
        edges = np.logspace(np.log10(fmin), np.log10(min(fmax, sr / 2 * 0.99)), n_bands + 1)
        self.band_masks = [(freqs >= edges[b]) & (freqs < edges[b + 1]) for b in range(n_bands)]
        self.band_center = np.array([(edges[b] + edges[b + 1]) / 2 for b in range(n_bands)])
        self.n_bands = n_bands
        self._prev = np.zeros(n_bands, dtype=np.float32)
        self._flux_avg = np.full(n_bands, 1e-6, dtype=np.float32)
        self._refractory = np.zeros(n_bands, dtype=np.float32)
        self._freqs = freqs
        self.t = 0.0
        self._onset_times: list[float] = []
        self.tempo = 120.0
        self._last_onset = -1.0

    def _classify(self, band: int, flatness: float) -> str:
        center = self.band_center[band]
        if center < 150.0:
            return "kick"
        if center >= 1800.0:
            return "hat" if flatness > 0.18 else "perc"
        return "snare" if flatness < 0.4 else "perc"

    def process(self, window_stereo: np.ndarray, dt: float) -> tuple[list[Event], float]:
        self.t += dt
        mono = window_stereo.mean(axis=1) if window_stereo.ndim == 2 else window_stereo
        spec = np.abs(np.fft.rfft(mono * self.window)).astype(np.float32)
        band = np.array([spec[m].sum() if m.any() else 0.0 for m in self.band_masks], dtype=np.float32)
        flux = np.maximum(band - self._prev, 0.0)
        self._prev = band

        a = (1.0 - math.exp(-dt / 0.25)) if dt > 0 else 1.0
        self._flux_avg += (flux - self._flux_avg) * a
        self._refractory = np.maximum(self._refractory - dt, 0.0)

        # Spectral flatness (noisiness): geo-mean / arith-mean.
        s = spec + 1e-9
        flatness = float(np.exp(np.mean(np.log(s))) / np.mean(s))

        # One hit spreads flux across bands -> emit the DOMINANT band's event (plus a
        # simultaneous hat if the dominant is a kick), not one event per band.
        ratio = flux / (self._flux_avg * self.threshold + 1e-9)
        ok = (ratio > 1.0) & (flux > 0.4) & (self._refractory <= 0)
        events: list[Event] = []
        if ok.any():
            order = np.argsort(ratio)[::-1]
            db = int(order[0])
            if ok[db]:
                events.append(Event(self._classify(db, flatness),
                                    float(min(1.0, ratio[db] / 3.0))))
                self._refractory[db] = 0.05 if self.band_center[db] >= 1800 else 0.09
                self._track_tempo()
                if self.band_center[db] < 150.0:  # kick + simultaneous hat is common
                    for hb in range(self.n_bands):
                        if self.band_center[hb] >= 1800 and ok[hb] and ratio[hb] > 1.5:
                            events.append(Event("hat", float(min(1.0, ratio[hb] / 3.0))))
                            self._refractory[hb] = 0.05
                            break
        return events, self.beat_phase()

    def _track_tempo(self) -> None:
        if self._last_onset >= 0:
            ioi = self.t - self._last_onset
            if 0.25 <= ioi <= 1.2:  # 50..240 BPM beat range
                self._onset_times.append(ioi)
                self._onset_times = self._onset_times[-16:]
                self.tempo = 60.0 / float(np.median(self._onset_times))
        self._last_onset = self.t

    def beat_phase(self) -> float:
        if self._last_onset < 0 or self.tempo <= 0:
            return 0.0
        return ((self.t - self._last_onset) / (60.0 / self.tempo)) % 1.0
