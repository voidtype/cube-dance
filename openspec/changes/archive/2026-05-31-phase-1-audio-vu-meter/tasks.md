## 1. Dependencies & layout

- [x] 1.1 Add `soundfile` and `sounddevice` via `uv add`.
- [x] 1.2 Create `cube_dance/audio/{__init__,file,source,demo}.py` and `cube_dance/visuals/{__init__,base,placeholder,vu}.py`.

## 2. Audio file + analysis (pure numpy, headless-testable)

- [x] 2.1 `audio/file.py`: `AudioFile` — load via `soundfile` (sample rate, duration, channels, mono mix); `from_array` constructor; clear error on missing/unreadable file.
- [x] 2.2 `audio/file.py`: per-hop RMS **loudness envelope**, normalised to `[0,1]` by a high percentile; `level_at(t)` with position clamping.
- [x] 2.3 `audio/demo.py`: synthesise a deterministic ~8 s 120 BPM kick+hat signal returning an `AudioFile`.

## 3. Transport + playback

- [x] 3.1 `audio/source.py`: `AudioSource` transport — `play/pause/restart/seek`, `position`, `playing`, `finished`; virtual clock advanced by `update(dt)`; `level()` via the envelope.
- [x] 3.2 `audio/source.py`: live playback via `sounddevice` (lazy import, guarded); stream callback feeds samples and advances the frame counter so `position` follows the audio; `--mute`/no-device/error falls back to the virtual clock without raising.

## 4. Visualisation layer

- [x] 4.1 `visuals/base.py`: a `Visual` protocol `update(model, t, features)`; `visuals/placeholder.py`: wrap the Phase 0 pattern as `PlaceholderVisual`.
- [x] 4.2 `visuals/vu.py`: `VuMeter` — envelope follower (fast attack / slow release); vectorised vertical fill (`lit if normalised height ≤ displayed level`), green→amber→red ramp by height, level-driven brightness, decaying peak-hold band.

## 5. Integration

- [x] 5.1 `app.py`: build an `AudioSource` when `--audio`/`--demo` is set and use `VuMeter`; otherwise `PlaceholderVisual`; advance transport + visual each frame from the audio position.
- [x] 5.2 `app.py`: transport keys `K` (play/pause) and `J` (restart); HUD shows position/duration + play state when audio is active.
- [x] 5.3 `cli.py`: add `--audio PATH`, `--demo`, `--mute`; wire into the app and `--selftest`.

## 6. Self-test & tests

- [x] 6.1 `selftest.py`: extend so `--selftest --demo` builds the demo audio, advances the transport + VU offline for N frames, and reports level/fill stats with no device/window.
- [x] 6.2 `tests/`: `AudioFile` (metadata via a generated WAV, envelope louder>quieter, `level_at` clamping, `from_array`), and `AudioSource` virtual mode (position advances only while playing; seek/restart; muted start does not raise).
- [x] 6.3 `tests/`: `VuMeter` (fill fraction ≈ level after settling; green near floor / red near top; release decays gradually) and `PlaceholderVisual` fallback writes the buffer.

## 7. Verify & document

- [x] 7.1 `uv run pytest` and `uv run cube-dance --selftest --demo` pass green; offscreen render a VU frame to sanity-check.
- [x] 7.2 Update `README.md`: `--audio`/`--demo`/`--mute`, transport keys, and supported formats.
- [x] 7.3 `openspec validate phase-1-audio-vu-meter --strict` passes.

- [x] 7.4 Open the audio device on a background thread so the window never blocks on CoreAudio init; loop the `--demo` beat. (Fix: viewer appeared blank while the device opened.)
