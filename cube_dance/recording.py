"""Live-session recorder: capture the app's own rendered frames + the played
audio into a shareable MP4 (H.264 + AAC), via ffmpeg.

Two stages: (1) while recording, raw RGB frames are piped to an ffmpeg process
encoding H.264; (2) on stop, the audio segment that played is written to a WAV
and muxed with the video into the final timestamped .mp4. The HUD is excluded
because the app captures the framebuffer before drawing the overlay.
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import time

import numpy as np


def find_ffmpeg() -> str:
    """Locate ffmpeg: $CUBE_FFMPEG, then PATH, then the bundled imageio-ffmpeg."""
    env = os.environ.get("CUBE_FFMPEG")
    if env and os.path.exists(env):
        return env
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "ffmpeg not found. Install ffmpeg or `uv add imageio-ffmpeg`."
        ) from exc


def audio_segment(audio, start_s: float, dur_s: float, loop: bool) -> np.ndarray:
    """The `(m, channels)` samples for [start_s, start_s+dur_s).

    Wraps around for a looped source; zero-pads past the end otherwise.
    """
    sr = audio.sr
    data = audio.samples
    n = len(data)
    count = max(1, int(round(dur_s * sr)))
    start = int(round(start_s * sr))
    if n == 0:
        return np.zeros((count, data.shape[1] if data.ndim == 2 else 1), dtype=np.float32)
    if loop:
        idx = (start + np.arange(count)) % n
        return data[idx]
    seg = data[max(0, start) : start + count]
    if len(seg) < count:
        pad = np.zeros((count - len(seg), data.shape[1]), dtype=data.dtype)
        seg = np.concatenate([seg, pad], axis=0)
    return seg


class SessionRecorder:
    def __init__(self, audio_source=None, loop: bool = False, fps: int = 30, outdir: str = "recordings") -> None:
        self.audio_source = audio_source
        self.loop = loop
        self.fps = max(5, int(fps))
        self.outdir = outdir
        self._proc = None
        self._w = 0
        self._h = 0
        self._start_wall = 0.0
        self._start_pos = 0.0
        self._frame_index = 0  # frames written so far (paced to wall-clock)
        self._tmp_video: str | None = None
        self._final: str | None = None
        self.error: str | None = None

    @property
    def is_recording(self) -> bool:
        return self._proc is not None

    @property
    def elapsed(self) -> float:
        return (time.time() - self._start_wall) if self.is_recording else 0.0

    def start(self, w: int, h: int, now: float | None = None) -> None:
        if self.is_recording:
            return
        self.error = None
        w -= w % 2
        h -= h % 2
        if w < 2 or h < 2:
            self.error = "invalid frame size"
            return
        self._w, self._h = w, h
        os.makedirs(self.outdir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self._final = os.path.join(self.outdir, f"cube-{stamp}.mp4")
        self._tmp_video = self._final + ".video.mp4"
        try:
            ff = find_ffmpeg()
            cmd = [
                ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{w}x{h}", "-r", str(self.fps), "-i", "pipe:0",
                "-an", "-vf", "vflip", "-c:v", "libx264", "-preset", "veryfast",
                "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
                self._tmp_video,
            ]
            self._proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self._proc = None
            return
        self._start_wall = now if now is not None else time.time()
        self._start_pos = self.audio_source.position if self.audio_source is not None else 0.0
        self._frame_index = 0

    def frames_due(self, now: float) -> int:
        """How many frames to write *now* to keep the video at real-time.

        Paced against absolute wall-clock (not incrementally), so timing error
        can't accumulate: behind -> duplicate frames; ahead -> write none. This
        keeps the encoded duration equal to the real elapsed time, so it stays
        in sync with the muxed audio regardless of the render/capture rate.
        """
        if not self.is_recording:
            return 0
        target = int((now - self._start_wall) * self.fps) + 1
        n = target - self._frame_index
        if n <= 0:
            return 0
        return min(n, self.fps * 2)  # bound a single catch-up burst

    def write_frame(self, rgb_bytes: bytes, w: int, h: int, count: int = 1) -> None:
        if not self.is_recording or count <= 0:
            return
        try:
            if (w, h) != (self._w, self._h):
                from PIL import Image

                rgb_bytes = Image.frombytes("RGB", (w, h), rgb_bytes).resize((self._w, self._h)).tobytes()
            for _ in range(count):
                self._proc.stdin.write(rgb_bytes)
            self._frame_index += count
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            self._safe_kill()

    def stop(self) -> str | None:
        if not self.is_recording:
            return None
        proc = self._proc
        self._proc = None
        # Match the audio length to the encoded video exactly (frames / fps) so
        # the two streams are the same duration and stay in sync.
        video_dur = self._frame_index / self.fps if self._frame_index else max(0.1, time.time() - self._start_wall)
        try:
            proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.wait(timeout=30)
        except Exception:  # noqa: BLE001
            proc.kill()

        final, tmp_video = self._final, self._tmp_video
        if not (tmp_video and os.path.exists(tmp_video)):
            return None

        live = self.audio_source is not None and getattr(self.audio_source.audio, "is_live", False)
        if self.audio_source is not None and not live and self.audio_source.audio.duration > 0:
            try:
                import soundfile as sf

                seg = audio_segment(self.audio_source.audio, self._start_pos, video_dur, self.loop)
                tmp_wav = final + ".audio.wav"
                sf.write(tmp_wav, seg, self.audio_source.audio.sr)
                ff = find_ffmpeg()
                subprocess.run(
                    [ff, "-y", "-i", tmp_video, "-i", tmp_wav, "-c:v", "copy",
                     "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
                )
                os.remove(tmp_wav)
                os.remove(tmp_video)
            except Exception as exc:  # noqa: BLE001 - fall back to video-only
                self.error = str(exc)
                os.replace(tmp_video, final)
        else:
            os.replace(tmp_video, final)
        self._tmp_video = None
        return final

    def _safe_kill(self) -> None:
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                self._proc.kill()
            except Exception:  # noqa: BLE001
                pass
            self._proc = None
