"""Phase 6: live audio input ring buffer + AudioSource live mode."""

from __future__ import annotations

import numpy as np

from cube_dance.audio import AudioSource, LiveAudioInput


def _ramp(n, ch=2):
    r = np.arange(1, n + 1, dtype=np.float32)[:, None]
    return np.repeat(r, ch, axis=1)


def test_window_returns_latest_samples():
    live = LiveAudioInput(sr=1000, buffer_seconds=1.0)  # cap = 1000
    live._write(_ramp(300))  # 300 stereo frames
    w = live.window_at(0.0, 100)
    assert w.shape == (100, 2)
    assert np.allclose(w[:, 0], np.arange(201, 301))  # most recent 100


def test_mono_input_becomes_stereo():
    live = LiveAudioInput(sr=1000, buffer_seconds=0.5)
    live._write(np.arange(1, 51, dtype=np.float32)[:, None])  # mono
    w = live.window_at(0.0, 10)
    assert w.shape == (10, 2)
    assert np.allclose(w[:, 0], w[:, 1])
    assert np.allclose(w[:, 0], np.arange(41, 51))


def test_input_gain_scales():
    live = LiveAudioInput(sr=1000, buffer_seconds=0.5, gain=2.0)
    live._write(np.ones((20, 2), np.float32))
    assert np.allclose(live.window_at(0.0, 5), 2.0)


def test_ring_wraps_around():
    live = LiveAudioInput(sr=100, buffer_seconds=1.0)  # cap = 100
    live._write(_ramp(150))  # more than cap -> wraps
    assert np.allclose(live.window_at(0.0, 50)[:, 0], np.arange(101, 151))


def test_front_pad_when_underfilled():
    live = LiveAudioInput(sr=1000, buffer_seconds=1.0)
    live._write(np.full((5, 2), 3.0, np.float32))
    w = live.window_at(0.0, 20)
    assert np.allclose(w[-5:], 3.0) and np.allclose(w[:-5], 0.0)


def test_live_input_records_captured_audio():
    live = LiveAudioInput(sr=1000, buffer_seconds=0.5)
    live.start_record()
    live._write(np.full((100, 2), 0.3, np.float32))
    live._write(np.full((50, 2), 0.5, np.float32))
    seg = live.stop_record()
    assert seg.shape == (150, 2)
    assert np.allclose(seg[:100], 0.3) and np.allclose(seg[100:], 0.5)
    # after stop, nothing further is captured
    live._write(np.ones((10, 2), np.float32))
    assert live.stop_record().shape[0] == 0


def test_audiosource_live_mode():
    live = LiveAudioInput(sr=44100, buffer_seconds=1.0)
    src = AudioSource(live, mute=True)
    assert src._is_live and src.finished is False

    src.playing = True
    src.update(0.5)
    src.update(0.5)
    assert src.position >= 0.9  # wall-clock elapsed advances

    src.seek(0.0)
    assert src.position >= 0.9  # seek is inert for a live feed

    live._write(_ramp(4096) * 0.0 + 0.2)  # some signal in the ring
    feats = src.features(1 / 60)  # analyses the latest window, no crash
    assert hasattr(feats, "events") and isinstance(feats.events, list)
    assert src.finished is False  # never finishes
