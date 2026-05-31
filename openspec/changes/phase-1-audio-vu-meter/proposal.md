## Why

Phase 0 gave us an explorable cube and the `(N,3)` color-buffer contract, but the buffer
is only driven by a placeholder pattern. The whole point of the cube is to react to music.
Phase 1 makes the **first musical input** real: load an audio file into the simulation and
drive the cube as a **simple VU meter**, proving the audio → analysis → color-buffer path
that every later visual builds on.

## What Changes

- Add an **audio source** that loads an audio file (WAV/FLAC/AIFF/OGG via `soundfile`),
  exposes its sample rate and duration, and computes a normalised **loudness envelope**
  (per-hop RMS) so a level can be read at any playback position.
- Add a **transport**: play / pause / restart / seek-to-position, tracking the current
  playback position in seconds.
- **Play the audio out loud**, synced to the visualisation, via `sounddevice` (the visual
  position follows the audio stream). If no output device is available, degrade gracefully
  to a silent **virtual transport** (wall-clock driven) so the visuals still run.
- Add a **visualisation layer** that reads audio features and writes `model.colors`. Phase
  1 ships one visual — a **VU meter**: the cube fills from the floor up in proportion to
  the current level, with a green → amber → red ramp and a brief peak-hold cap, plus
  level-driven brightness. Smoothed with fast attack / slower release like a real meter.
- **Source selection**: when an audio file (or `--demo`) is provided the VU meter drives
  the buffer; otherwise the Phase 0 placeholder pattern remains the default.
- Add a **`--demo`** synthetic signal (a simple four-on-the-floor kick + hat) so the VU
  can be seen without supplying a file, and **`--audio PATH`** / **`--mute`** CLI options.
- Transport keybindings in the viewer (play/pause, restart) and a HUD line showing
  position / state.

Explicitly **out of scope** for Phase 1 (later phases): cube-aware regions / spatial
mapping (Phase 2 — e.g. corners = bass L/R), F1/MIDI input (Phase 3), the rich evolving
visual DSL (Phase 4), live audio-stream input (Phase 6), and MadMapper output (Phase 8).
Phase 1 is mono/global loudness only.

## Capabilities

### New Capabilities
- `audio-input`: Loading and decoding an audio file, a normalised loudness envelope and
  level-at-position query, a play/pause/seek transport, and synced playback to the output
  device with graceful silent fallback.
- `visualization`: A visual layer that maps audio features to the `(N,3)` color buffer,
  with a VU-meter visual for Phase 1 and selection between audio-driven and the no-audio
  placeholder.

### Modified Capabilities
<!-- None. The simulation-viewer still renders whatever is in model.colors; only the
     writer changes. The Phase 0 placeholder remains the no-audio default. -->

## Impact

- New dependencies: `soundfile` (libsndfile decode) and `sounddevice` (PortAudio output).
- New modules under `cube_dance/audio/` (source, transport, playback, demo synth) and
  `cube_dance/visuals/` (base + VU meter).
- New CLI options `--audio PATH`, `--demo`, `--mute`; new viewer transport keys + HUD.
- Builds directly on the Phase 0 `CubeModel.colors` contract; no change to geometry or
  the renderer. Establishes the audio-feature → visual interface that Phases 2/4/6 extend.
