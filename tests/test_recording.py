"""Tests for the session recorder: ffmpeg discovery, audio slicing, MP4 mux."""

from __future__ import annotations

import os
import subprocess
import time

import numpy as np
import pytest

from cube_dance.audio import AudioSource
from cube_dance.audio.demo import make_demo
from cube_dance.audio.file import AudioFile
from cube_dance.recording import SessionRecorder, audio_segment, find_ffmpeg


def test_find_ffmpeg_returns_existing_path():
    path = find_ffmpeg()
    assert os.path.exists(path)


def test_audio_segment_length_and_padding():
    sr = 100
    data = np.tile(np.arange(sr, dtype=np.float32)[:, None], (1, 2))  # 1 s ramp, stereo
    af = AudioFile.from_array(data, sr)

    seg = audio_segment(af, 0.0, 0.5, loop=False)
    assert seg.shape == (50, 2)
    assert np.allclose(seg[:, 0], np.arange(50))

    # Past the end, non-loop -> zero padded.
    seg = audio_segment(af, 0.9, 0.4, loop=False)
    assert seg.shape == (40, 2)
    assert np.allclose(seg[10:], 0.0)

    # Loop -> wraps around.
    seg = audio_segment(af, 0.9, 0.4, loop=True)
    assert seg.shape == (40, 2)
    assert seg[15, 0] < seg[5, 0]  # wrapped back to low indices


def _ffmpeg_has_stream(path: str, kind: str) -> bool:
    """True if `path` has a video (kind='v') or audio (kind='a') stream."""
    ff = find_ffmpeg()
    rc = subprocess.run(
        [ff, "-v", "error", "-i", path, "-map", f"0:{kind}:0", "-t", "0.1", "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode
    return rc == 0


def test_recorder_produces_mp4_with_video_and_audio(tmp_path):
    try:
        find_ffmpeg()
    except Exception:
        pytest.skip("no ffmpeg available")

    src = AudioSource(make_demo(), mute=True, loop=True)
    rec = SessionRecorder(audio_source=src, loop=True, fps=20, outdir=str(tmp_path))
    w, h = 64, 48
    rec.start(w, h)
    assert rec.is_recording and rec.error is None
    rec._start_wall = time.time() - 1.5  # simulate a 1.5 s capture window

    frame = (np.random.default_rng(0).integers(0, 255, (h, w, 3))).astype(np.uint8).tobytes()
    for i in range(30):
        rec.write_frame(frame, w, h, now=i / 20.0)

    path = rec.stop()
    assert path and os.path.exists(path) and os.path.getsize(path) > 1024
    assert path.endswith(".mp4")
    assert _ffmpeg_has_stream(path, "v")
    assert _ffmpeg_has_stream(path, "a")
