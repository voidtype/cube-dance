## Why

The cube-aware visual is one fixed mapping. Phase 4 makes the visuals **rich, evolving, and
authorable**, driven by **classified musical events** rather than raw bands. The agreed
architecture: a streaming **event-detection** pipeline (multi-band onset → per-transient
features → drum/instrument class) plus a separate **sustained bass** stream, feeding a
**Python element engine** where visual elements **subscribe** to events; with **beat +
energy auto-evolution** and some **composition awareness** so a set keeps changing.

## What Changes

- **Event detection (streaming, heuristic, low-latency).** Two parallel streams from one
  filterbank/STFT:
  - **Transient/onset path** — per-band **spectral-flux** onset detection (separate bands so
    low and high hits are independent), then per-onset **features** (band energy, spectral
    centroid, flatness/noisiness, decay) → **classify** into `kick` / `snare` / `hat` /
    `perc` by heuristic thresholds (frequency extremes are the easy wins). Output: discrete
    **events** `(class, strength, time)`.
  - **Sustained bass path** — an **envelope follower** on the sub band (~30–120 Hz), a
    continuous value (+ its rate of change for "bass is doing something"). **Kick vs bass**
    is resolved by **attack sharpness/duration** (short spike → kick event; sustained →
    bass level), not one detector.
  - Heuristics first; structured so a small classifier can replace the thresholds later.
- **Element engine (Python).** A `VisualEngine` holds composable **elements**; each reads a
  shared **context** (events this frame + continuous features + beat phase + time) and
  writes into the `(N,3)` buffer with a blend mode and a region/palette. Elements
  **subscribe** to events (e.g. "on kick → flash corners", "on hat → sparkle beams") and to
  continuous streams (bass env → corner brightness). Built-ins: `BassCorners`,
  `SpectrumBeams`, `KickPulse`, `HatSparkle`, `Sweep`, `Chase`, `AmbientWash`. Per-element
  **modulators** (LFO / feature-envelope / time evolver).
- **Composition awareness + evolution.** A lightweight composition state tracks energy and
  onset density to sense build-ups/drops; an energy accumulator + **accelerating** evolvers
  rotate palettes and grow intensity/complexity over a set.
- **Python preset system.** A preset is a Python module exposing `build(engine, ctx)` that
  instantiates elements and wires their event subscriptions/modulators. Built-in presets;
  select with `--preset` and cycle live. (Hot-reload / F1-driven selection come in Phase 5.)
- The default `spectrum` visual becomes the preset-driven element engine; `vu` + placeholder
  remain.

Out of scope (later): F1 → preset/evolution roles (Phase 5), live audio input (Phase 6),
extra surfaces (Phase 7), MadMapper output (Phase 8), and ML classification (heuristics now).

## Capabilities

### New Capabilities
- `event-detection`: streaming multi-band onset detection + per-transient classification
  (kick/snare/hat/perc) and a sustained bass-envelope stream, with kick-vs-bass disambiguation.
- `visual-engine`: the Python element engine — elements that subscribe to events/features,
  blended into the buffer, with modulators, composition awareness, and energy/beat evolution.
- `preset-system`: Python preset modules that build element graphs; built-ins + selection.

### Modified Capabilities
- `visualization`: the default cube-aware visual becomes the preset-driven element engine;
  features are extended with classified events + bass envelope + beat phase.

## Impact

- New dep: none required (numpy/scipy suffice; `pyyaml` only if we later add YAML export).
  New `cube_dance/audio/events.py`, `cube_dance/visuals/engine/` (context, element, engine,
  elements, modulators), `cube_dance/presets/` (Python presets + loader). `app.py`/`cli.py`
  gain `--preset` + cycle. No change to the `(N,3)` buffer or geometry.
