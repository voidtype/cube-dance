"""Tests for audio file decode/analysis and the transport (offline / virtual)."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from cube_dance.audio import AudioFile, AudioSource
from cube_dance.audio.demo import make_demo


def test_from_array_metadata():
    sr = 44100
    data = np.zeros((sr, 2), dtype=np.float32)
    af = AudioFile.from_array(data, sr)
    assert af.sr == sr
    assert af.channels == 2
    assert abs(af.duration - 1.0) < 1e-3
    assert af.mono.shape == (sr,)


def test_load_wav_and_missing_file(tmp_path):
    sr = 22050
    x = 0.3 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr)
    p = tmp_path / "tone.wav"
    sf.write(str(p), x.astype("float32"), sr)

    af = AudioFile.load(str(p))
    assert af.sr == sr
    assert abs(af.duration - 1.0) < 1e-3

    with pytest.raises(FileNotFoundError):
        AudioFile.load(str(tmp_path / "nope.wav"))


def test_envelope_louder_than_quieter():
    sr = 44100
    loud = 0.8 * np.sin(2 * np.pi * 200 * np.arange(sr // 2) / sr)
    quiet = 0.03 * np.sin(2 * np.pi * 200 * np.arange(sr // 2) / sr)
    af = AudioFile.from_array(np.concatenate([loud, quiet]).astype("float32"), sr)
    assert af.level_at(0.25) > af.level_at(0.75)
    assert 0.0 <= af.level_at(0.75) <= 1.0


def test_level_at_clamps():
    af = make_demo()
    assert 0.0 <= af.level_at(-5.0) <= 1.0
    assert 0.0 <= af.level_at(af.duration + 5.0) <= 1.0


def test_transport_advances_only_while_playing():
    src = AudioSource(make_demo(), mute=True)
    src.start()  # muted -> virtual clock, must not raise
    assert src.playing
    for _ in range(60):
        src.update(1 / 60)
    assert abs(src.position - 1.0) < 0.05

    src.pause()
    held = src.position
    for _ in range(60):
        src.update(1 / 60)
    assert abs(src.position - held) < 1e-6


def test_seek_restart_and_finished():
    src = AudioSource(make_demo(), mute=True)
    src.start()
    src.seek(0.5)
    assert abs(src.position - 0.5) < 1e-6
    src.restart()
    assert src.position == 0.0
    src.seek(src.duration + 10)
    assert abs(src.position - src.duration) < 1e-6
    assert src.finished
