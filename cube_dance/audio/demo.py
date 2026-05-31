"""A deterministic synthetic demo signal (four-on-the-floor kick + off-beat hats)
so the VU meter can be seen without supplying an audio file.
"""

from __future__ import annotations

import numpy as np

from .file import AudioFile


def make_demo(sr: int = 44100, bpm: float = 120.0, bars: int = 4) -> AudioFile:
    beat = 60.0 / bpm
    total = beat * 4 * bars
    n = int(total * sr)
    out = np.zeros(n, dtype=np.float32)
    n_beats = int(round(total / beat))

    # Kick on every beat: pitch-dropping sine + a short click transient.
    for b in range(n_beats):
        start = int(b * beat * sr)
        dur = int(0.25 * sr)
        env = np.exp(-np.linspace(0.0, 1.0, dur) * 18.0)
        freq = np.linspace(120.0, 45.0, dur)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        kick = np.sin(phase) * env * 0.9
        kick[:60] += np.linspace(1.0, 0.0, 60) * 0.5
        seg = slice(start, min(start + dur, n))
        out[seg] += kick[: seg.stop - seg.start]

    # Closed hats on the off-beats.
    for h in range(n_beats * 2):
        if h % 2 == 1:
            start = int(h * (beat / 2) * sr)
            dur = int(0.05 * sr)
            env = np.exp(-np.linspace(0.0, 1.0, dur) * 40.0)
            noise = np.random.default_rng(h).standard_normal(dur).astype(np.float32) * env * 0.25
            seg = slice(start, min(start + dur, n))
            out[seg] += noise[: seg.stop - seg.start]

    out = np.clip(out, -1.0, 1.0)
    stereo = np.stack([out, out], axis=1)
    return AudioFile.from_array(stereo, sr)
