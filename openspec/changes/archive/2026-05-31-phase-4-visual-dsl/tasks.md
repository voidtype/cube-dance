## 1. Event detection

- [x] 1.1 `audio/events.py`: `Event` (class, strength) + `EventDetector` — per-band spectral flux onset detection (moving-average threshold + per-class refractory), per-onset features (band, centroid, flatness, energy), heuristic classify → kick/snare/hat/perc; streaming `process(window, dt) -> (events, bass_level, bass_rate)`.
- [x] 1.2 `audio/events.py`: sub-band envelope follower (~30–120 Hz) for the sustained bass level; kick-vs-bass by attack sharpness/duration.
- [x] 1.3 `audio/events.py`: lightweight tempo/phase from inter-onset intervals (beat phase).

## 2. Element engine

- [x] 2.1 `visuals/engine/context.py`: `Context` (events, features, beat, t, dt, model) + `Modulator`s (LFO, feature-envelope, time-evolver with acceleration).
- [x] 2.2 `visuals/engine/element.py`: `Element` base (region, palette, blend, event subscription, decaying trigger envelope).
- [x] 2.3 `visuals/engine/elements.py`: `BassCorners`, `SpectrumBeams`, `KickPulse`, `HatSparkle`, `Sweep`, `Chase`, `AmbientWash`.
- [x] 2.4 `visuals/engine/engine.py`: `VisualEngine` — run + composite elements; hold context; `Composition` energy/density tracker + energy-accumulator evolution (accelerating).

## 3. Feature plumbing + presets

- [x] 3.1 `audio/source.py` / `Features`: carry classified events + bass level + beat phase (from the `EventDetector`).
- [x] 3.2 `presets/`: a loader (`load(name)`) + built-ins (e.g. `deep`, `punchy`); each a Python module with `build(engine)`.
- [x] 3.3 `visuals/engine` adapter as a `Visual` (so it slots into the existing selection); default `spectrum`/auto uses the engine with the selected preset.

## 4. Integration

- [x] 4.1 `app.py`/`cli.py`: `--preset NAME` (default a built-in); build the engine + preset; feed events/features each frame; key to cycle presets.

## 5. Verify & document

- [x] 5.1 `tests/`: event detector classifies synthetic kick (low/sharp) vs hat (high/noisy); sustained bass → high level + not a kick stream; engine composites elements; a kick event triggers a subscribed element; preset loads + unknown errors; evolution advances under sustained energy.
- [x] 5.2 `uv run pytest` green; `--selftest --demo` exercises the engine; offscreen renders of a preset (a few moments).
- [x] 5.3 Update `README.md` (presets, `--preset`, event-driven visuals).
- [x] 5.4 `openspec validate phase-4-visual-dsl --strict` passes.
