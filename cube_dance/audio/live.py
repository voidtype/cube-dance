"""Live audio input: capture a `sounddevice` input stream into a rolling ring
buffer and expose the same windowed contract as :class:`AudioFile`.

The whole analysis path is streaming (a window at the playhead), so a live source
just needs to answer ``window_at(t, win)`` with the **latest** ``win`` samples.
The device opens on a background thread (PortAudio can block for seconds) and
degrades to silence if it is unavailable. Mono inputs are presented as stereo so
the L/R features are unchanged.
"""

from __future__ import annotations

import threading

import numpy as np


def list_input_devices() -> list[str]:
    """Human-readable lines for the available input devices (best effort)."""
    try:
        import sounddevice as sd

        out = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) > 0:
                out.append(f"[{i}] {d['name']}  ({d['max_input_channels']} ch, "
                           f"{int(d.get('default_samplerate', 0))} Hz)")
        return out
    except Exception as exc:  # noqa: BLE001 - no backend / no devices
        return [f"(could not query input devices: {exc})"]


class LiveAudioInput:
    """A capture-only audio source with the :class:`AudioFile` windowed interface."""

    is_live = True

    def __init__(self, sr: int = 44100, device=None, gain: float = 1.0,
                 buffer_seconds: float = 4.0, request_channels: int = 2) -> None:
        self.sr = int(sr)
        self.device = device
        self.gain = float(gain)
        self.channels = 2  # always present stereo (mono is duplicated)
        self._req = int(request_channels)
        self.cap = max(1, int(self.sr * buffer_seconds))
        self._buf = np.zeros((self.cap, self.channels), dtype=np.float32)
        self._w = 0
        self._lock = threading.Lock()
        self._stream = None
        self.duration = float(buffer_seconds)  # rolling window length (no real length)
        self.active = False
        self.error: str | None = None

    # --- Lifecycle -----------------------------------------------------------
    def start(self) -> None:
        threading.Thread(target=self._open, daemon=True).start()

    def _open(self) -> None:  # pragma: no cover - needs an audio device
        import sounddevice as sd

        def callback(indata, frames, time_info, status) -> None:
            self._write(indata)

        for ch in (self._req, 1):  # fall back to mono if stereo open fails
            try:
                stream = sd.InputStream(
                    samplerate=self.sr, channels=ch, dtype="float32",
                    device=self.device, callback=callback,
                )
                stream.start()
                self._stream = stream
                self.active = True
                self.error = None
                return
            except Exception as exc:  # noqa: BLE001
                self.error = str(exc)
        self.active = False

    def close(self) -> None:
        if self._stream is not None:  # pragma: no cover - device
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        self.active = False

    # --- Capture -------------------------------------------------------------
    def _write(self, indata) -> None:
        x = np.asarray(indata, dtype=np.float32)
        if x.ndim == 1:
            x = x[:, None]
        if x.shape[1] == 1:  # mono -> stereo
            x = np.repeat(x, 2, axis=1)
        elif x.shape[1] != self.channels:
            x = x[:, : self.channels]
        if self.gain != 1.0:
            x = x * self.gain
        n = x.shape[0]
        if n == 0:
            return
        with self._lock:
            w = self._w
            end = w + n
            if end <= self.cap:
                self._buf[w:end] = x
            else:
                first = self.cap - w
                self._buf[w:] = x[:first]
                self._buf[: n - first] = x[first:]
            self._w = (w + n) % self.cap

    # --- Windowed access (same contract as AudioFile) ------------------------
    def window_at(self, t: float, win: int) -> np.ndarray:
        """The latest ``(win, channels)`` block of captured audio (``t`` ignored)."""
        out = np.zeros((win, self.channels), dtype=np.float32)
        with self._lock:
            w = self._w
            take = min(win, self.cap)
            start = (w - take) % self.cap
            if start + take <= self.cap:
                seg = self._buf[start:start + take].copy()
            else:
                first = self.cap - start
                seg = np.empty((take, self.channels), dtype=np.float32)
                seg[:first] = self._buf[start:]
                seg[first:] = self._buf[: take - first]
        out[win - take:] = seg  # front-pad if win > cap
        return out

    def level_at(self, t: float, win: int = 2048) -> float:
        w = self.window_at(t, win)
        return float(min(1.0, np.sqrt(np.mean(w.mean(axis=1) ** 2))))
