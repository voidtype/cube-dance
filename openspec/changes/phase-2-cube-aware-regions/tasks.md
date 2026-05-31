## 1. Audio bands

- [x] 1.1 Add `scipy` via `uv add`.
- [x] 1.2 `audio/file.py`: compute per-hop **band envelopes** (bass/mid/treble) for left, right, and mono via Butterworth band filters + per-hop RMS, each normalised to `[0,1]`.
- [x] 1.3 `audio/file.py`: `bands_at(t)` returning the band values (mono + L/R) at a clamped position.
- [x] 1.4 `audio/source.py`: `features()` returning a `Features` (level + bands) at the current position.

## 2. Model regions

- [x] 2.1 `led_topology.py`: precompute `region_indices` for `left/right` (X), `bottom/top` (Y), `front/back` (Z); expose alongside edge/corner sets.

## 3. Visualisation

- [x] 3.1 `visuals/base.py`: extend `Features` with `bass, mid, treble, bass_l, bass_r` (defaults 0).
- [x] 3.2 `visuals/cube_aware.py`: `CubeAwareVisual` — corners ← bass (left/right split by channel, warm hue), beams ← mid/treble (cool hue), per-band envelope followers, slow hue drift; vectorised over region index sets.
- [x] 3.3 `app.py`/`cli.py`: `--visual {auto,spectrum,vu}` (default auto); build the chosen visual (auto → cube-aware with audio, else placeholder); pass full `features()` each frame; HUD shows the visual name.

## 4. Verify & document

- [x] 4.1 `tests/`: bands separate frequency content (bass-heavy vs treble-heavy synthetic signals) and split L/R; `region_indices` partition the pixels; `CubeAwareVisual` brightens corners on bass and edges on treble, and left>right corners when bass_l>bass_r.
- [x] 4.2 `uv run pytest` green; `--selftest --demo` exercises the cube-aware visual offline; offscreen render to eyeball (bass→corners, treble→beams).
- [x] 4.3 Update `README.md` (`--visual`, what the cube-aware visual does).
- [x] 4.4 `openspec validate phase-2-cube-aware-regions --strict` passes.
