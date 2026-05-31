"""Transport + (optional) synced playback for an :class:`AudioFile`.

The audio output device is opened on a **background thread** so the window never
blocks waiting for CoreAudio/PortAudio (which can take seconds). Until the device
stream is live, the position is advanced by the caller's per-frame ``dt`` (a
silent virtual clock); once the stream is live the position follows the audio
stream's frame counter, so visuals and sound can't drift.
"""

from __future__ import annotations

import threading

from .file import AudioFile


class AudioSource:
    def __init__(self, audio: AudioFile, mute: bool = False, loop: bool = False) -> None:
        self.audio = audio
        self.mute = mute
        self.loop = loop
        self.playing = False
        self._pos = 0.0  # virtual-clock position (seconds)
        self._frame = 0  # live-clock frame counter
        self._live = False
        self._opening = False
        self._stream = None
        self._lock = threading.Lock()

    # --- Position / state ----------------------------------------------------
    @property
    def duration(self) -> float:
        return self.audio.duration

    @property
    def position(self) -> float:
        if self._live:
            with self._lock:
                secs = self._frame / self.audio.sr
            return secs % self.duration if self.loop and self.duration else min(secs, self.duration)
        return self._pos

    @property
    def finished(self) -> bool:
        return (not self.loop) and self.position >= self.duration - 1e-3

    def level(self) -> float:
        return self.audio.level_at(self.position)

    def bands(self) -> dict[str, float]:
        """bass/mid/treble (mono) + bass_l/bass_r at the current position."""
        return self.audio.bands_at(self.position)

    # --- Lifecycle / transport ----------------------------------------------
    def start(self) -> None:
        """Begin playback. Returns immediately; the device opens in the background."""
        self.playing = True
        if not self.mute:
            self._spawn_open()

    def _spawn_open(self) -> None:
        if self._opening or self._live or self._stream is not None:
            return
        self._opening = True
        threading.Thread(target=self._open_stream, daemon=True).start()

    def _open_stream(self) -> None:  # pragma: no cover - needs an audio device
        try:
            import sounddevice as sd

            data = self.audio.samples
            channels = data.shape[1]
            n = len(data)
            with self._lock:
                self._frame = int(self._pos * self.audio.sr)

            def callback(outdata, frames, time_info, status) -> None:
                with self._lock:
                    start = self._frame
                end = start + frames
                if end <= n:
                    outdata[:] = data[start:end]
                    with self._lock:
                        self._frame = end
                    return
                first = n - start
                outdata[:first] = data[start:]
                if self.loop:
                    rem = frames - first
                    outdata[first:] = data[:rem]
                    with self._lock:
                        self._frame = rem
                else:
                    outdata[first:] = 0.0
                    with self._lock:
                        self._frame = n
                    raise sd.CallbackStop

            stream = sd.OutputStream(
                samplerate=self.audio.sr, channels=channels, dtype="float32", callback=callback
            )
            stream.start()
            with self._lock:
                self._stream = stream
                self._live = True
                self._opening = False
            if not self.playing:  # user paused during the open
                try:
                    stream.stop()
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001 - no device / error -> stay on virtual clock
            with self._lock:
                self._opening = False
                self._live = False
                self._stream = None

    def update(self, dt: float) -> None:
        """Advance the virtual clock (no-op once the device stream is live)."""
        if self.playing and not self._live:
            self._pos += max(dt, 0.0)
            if self._pos >= self.duration:
                if self.loop and self.duration:
                    self._pos %= self.duration
                else:
                    self._pos = self.duration
                    self.playing = False

    def play(self) -> None:
        if self.finished:
            self.seek(0.0)
        self.playing = True
        if self._stream is not None:
            try:  # pragma: no cover - device
                self._stream.start()
            except Exception:  # noqa: BLE001
                pass
        elif not self.mute and not self._live:
            self._spawn_open()

    def pause(self) -> None:
        self.playing = False
        if self._stream is not None:
            try:  # pragma: no cover - device
                self._stream.stop()
            except Exception:  # noqa: BLE001
                pass

    def toggle(self) -> None:
        self.pause() if self.playing else self.play()

    def restart(self) -> None:
        self.seek(0.0)

    def seek(self, t: float) -> None:
        t = min(max(t, 0.0), self.duration)
        self._pos = t
        if self._live:
            with self._lock:
                self._frame = int(t * self.audio.sr)

    def close(self) -> None:
        if self._stream is not None:  # pragma: no cover - device
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
        self._live = False
