## Why

Everything so far runs off a loaded file, but the rig is for live events — the music
comes off the DJ's output, not a file. Phase 6 adds a **live audio input stream** so the
whole pipeline (onset detection → events → decks) runs off real-time sound. The analysis was
built **streaming from day one** (a window at the playhead, no precompute), specifically so
this drops in behind the same `window_at(t, win)` contract.

## What Changes

- **`LiveAudioInput`** — opens a `sounddevice` **input stream** (line/mic) on a background
  thread and writes into a **rolling ring buffer**. It duck-types the file source
  (`sr`, `channels`, `window_at`, `level_at`) but `window_at` always returns the **latest**
  `win` samples (live = "now"); it presents **stereo** (mono inputs are duplicated) so the
  L/R features keep working. An **input gain** scales the captured signal; `is_live = True`
  marks it.
- **`AudioSource` live mode** — when the source is live, there is **no output playback** (the
  sound is already in the room) and **no transport/seek** (you can't seek live); the position
  is a wall-clock elapsed time for the HUD, and `features(dt)` analyses the latest window
  exactly as before. It never "finishes".
- **CLI** — `--live` selects the input source; `--input-device NAME|INDEX` picks the device;
  `--list-audio-inputs` prints the available input devices and exits; `--input-gain G` scales
  the level.
- **Viewer** — the HUD shows a **LIVE** indicator and elapsed time (no total/transport);
  device-open is non-blocking and degrades cleanly to silence if no device is available.
- **Recording** in live mode is **video-only** for now (no file to mux; capturing the live
  input to the MP4 is a later follow-up).

Out of scope (later phases): extra surfaces (Phase 7), MadMapper video output (Phase 8),
muxing captured live audio into recordings.

## Impact

- Specs: `audio-input` (live input source + live transport semantics), `simulation-viewer`
  (CLI flags, LIVE HUD), `recording` (video-only when live).
- Code: new `audio/live.py`; `audio/source.py` (live mode), `audio/__init__.py`,
  `recording.py` (guard), `cli.py`, `app.py`, tests.
- The streaming `window_at`/`features` contract and the `(N,3)` buffer are unchanged.
