## Context

`AudioFile.window_at(t, win)` returns the `(win, channels)` block ending at position `t`,
front-padded near the start — explicitly "the same interface a live ring buffer will
provide." `AudioSource` owns the analyzer/processor/event-detector and, for a file, an
**output** stream plus a frame/virtual clock. Live input needs the same window access but is
**capture-only** and always "now".

## Decisions

### A rolling ring buffer behind the same contract

- `LiveAudioInput` holds a `(cap, 2)` float32 ring (`cap = sr * buffer_seconds`, ~4 s). A
  `sounddevice.InputStream` callback writes incoming frames at a wrapping write index under a
  lock. `window_at(t, win)` ignores `t` and returns the most recent `win` samples (handling
  wrap); `level_at` mirrors the file. Always **stereo**: mono inputs are duplicated so the
  L/R bass/beam features are unchanged.
- Device open happens on a **background thread** (PortAudio can block for seconds), matching
  the existing output-stream pattern; failure leaves the buffer silent and records an error.
- Channels are stored as 2 regardless of the device: the `_write` step coerces 1→2 (duplicate)
  or N→2 (take first two), so the buffer shape is stable and analysis code is untouched.

### Live mode in AudioSource, detected via `is_live`

- `AudioSource` checks `getattr(audio, "is_live", False)`. In live mode `start()` opens the
  **input** stream (no output spawn), `update(dt)` advances a wall-clock `position` for the
  HUD only, `finished` is always False, and `play/pause/seek/restart` are inert (you can't
  seek a live feed). `features(dt)` is unchanged — `window_at` returns the latest window.
- `close()` closes the live input via `audio.close()`.

### Why no monitoring (output) in live mode

The DJ's signal is already on the PA; echoing it through the app's output would double it and
add latency. So live mode never opens an output stream. (A future `--monitor` could add it.)

### Recording

`SessionRecorder` muxes `audio_source.audio.samples` for a file. A live source has no full
buffer, so recording in live mode is **video-only** (guarded by `is_live`). Capturing the
live input to a WAV during recording is a clean follow-up but out of scope here.

## Risks / Trade-offs

- **No device / permissions** (mic access) — the background open catches errors and stays
  silent; `--list-audio-inputs` helps pick a device. The viewer still runs.
- **Latency** — visual reaction is bounded by the input block size + analysis window; the
  ring keeps a few seconds so `window_at` always has data. Good enough for a light show.
- **Headless tests** can't open a real device, so tests feed the ring via the callback path
  directly (`_write`) and assert `window_at` returns the latest samples.
