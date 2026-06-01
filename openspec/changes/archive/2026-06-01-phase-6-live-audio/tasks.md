## 1. Live input source

- [x] 1.1 `audio/live.py`: `LiveAudioInput` — background `sounddevice.InputStream` into a
      rolling stereo ring buffer; `window_at(t, win)` returns the latest window (wrap-safe),
      `level_at`, `sr`, `channels=2`, `is_live=True`, input `gain`, `start()`/`close()`,
      mono→stereo coercion, error-tolerant open.
- [x] 1.2 `audio/__init__.py`: export `LiveAudioInput`.

## 2. AudioSource live mode

- [x] 2.1 `audio/source.py`: detect `is_live`; `start()` opens the input (no output spawn);
      `update(dt)` advances a wall-clock position; `finished` False; `play/pause/seek/restart`
      inert; `close()` closes the live input.

## 3. CLI + viewer + recording

- [x] 3.1 `cli.py`: `--live`, `--input-device`, `--input-gain`, `--list-audio-inputs` (print
      input devices + exit); build a `LiveAudioInput` for `--live`.
- [x] 3.2 `app.py`: LIVE HUD line (indicator + elapsed, no transport); pass the live source to
      `AudioSource`; keep device-open non-blocking.
- [x] 3.3 `recording.py`: video-only when the source `is_live`.

## 4. Verify & document

- [x] 4.1 `tests/test_phase6.py`: ring buffer returns the latest window; mono→stereo; gain;
      `AudioSource` live mode (position advances, never finished, seek inert, features run).
- [x] 4.2 `uv run pytest` green; `--list-audio-inputs` works; a guarded live smoke (skips if
      no device).
- [x] 4.3 Update `README.md` (live input: `--live`, device selection); note video-only live
      recording.
- [x] 4.4 `openspec validate phase-6-live-audio --strict` passes.
