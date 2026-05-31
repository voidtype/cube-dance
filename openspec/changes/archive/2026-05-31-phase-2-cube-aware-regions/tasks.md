## 1. Streaming audio analysis (no precompute)

- [x] 1.1 Add `scipy` via `uv add` (available; FFT path uses numpy).
- [x] 1.2 `audio/analysis.py`: `SpectrumAnalyzer` — per-window FFT into log-spaced, per-channel frequency buckets (streaming; reusable for a live ring buffer).
- [x] 1.3 `audio/file.py`: drop all load-time precompute; expose `window_at(t, win)` (the live-buffer-shaped interface) + a simple windowed `level_at`.
- [x] 1.4 `audio/processor.py`: `FeatureProcessor` + `AgcParams` — per-bucket auto-level + global presence gate (quiet hides exponentially), streaming/stateful.
- [x] 1.5 `audio/source.py`: own the analyzer + processor; `features(dt)` analyses the window at the current position.

## 2. Model regions

- [x] 2.1 `led_topology.py`: precompute `region_indices` for left/right, bottom/top, front/back.

## 3. Visualisation

- [x] 3.1 `visuals/base.py`: `Features` carries per-channel bucket arrays + aggregates.
- [x] 3.2 `visuals/params.py`: `VisualParams` (for the DSL).
- [x] 3.3 `visuals/cube_aware.py`: corners ← bass (L/R); beams ← spectrum-along-beam, lateralised by stereo; AGC-driven brightness (stark); per-frequency hue that drifts and accelerates over time.
- [x] 3.4 `app.py`/`cli.py`: `--visual {auto,spectrum,vu}`; pass streaming `features(dt)` each frame; HUD shows the visual name.

## 4. Verify & document

- [x] 4.1 `tests/`: analyzer separates frequencies + channels; AGC hides quiet sections yet levels a quiet track; regions partition; cube-aware corners split L/R on bass and beams react to buckets.
- [x] 4.2 `uv run pytest` green; `--selftest --demo` exercises the cube-aware visual; offscreen render (demo + panned) to eyeball stereo + spectrum + colour.
- [x] 4.3 Update `README.md`.
- [x] 4.4 `openspec validate phase-2-cube-aware-regions --strict` passes.
