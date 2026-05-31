## Why

Phase 1 drives the whole cube from one overall loudness number. The cube has a rich
spatial structure (8 corners, 12 beams, left/right/top/bottom) that should be used: make
the software **cube-aware** so different parts of the music light different parts of the
cube. Per the roadmap: **corners = bass (split left/right), beams = treble/mids**.

## What Changes

- Extend **audio analysis** from a single loudness level to **frequency bands** — bass /
  mid / treble — computed per **stereo channel** (so we have left-bass and right-bass) and
  mono, as normalised envelopes queryable at any playback position (same precompute-on-load
  approach as the Phase 1 level).
- Add **spatial region groupings** to the cube model: left/right (by X), top/bottom (by Y),
  front/back (by Z), plus the existing edge/corner sets — so visuals can target regions.
- Extend the visual **features** passed each frame from `{level}` to also carry the band
  energies (`bass`, `mid`, `treble`, `bass_l`, `bass_r`).
- Add a **cube-aware visual**: **corners** pulse with **bass**, split **left/right** by
  channel (left corners ← left-bass, right corners ← right-bass); **beams** respond to
  **mid/treble** (a brighter, cooler shimmer). Smoothed per band and gently evolving in hue
  over time.
- Add a **`--visual`** selector (`spectrum` cube-aware | `vu` Phase-1 meter | `auto`);
  default `auto` → the cube-aware visual when audio is present, else the placeholder.

Out of scope (later phases): the rich DSL-driven evolving visuals (Phase 4), F1 control
(Phase 3/5), live input (Phase 6). Phase 2 is the first spatial/cube-aware mapping.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `audio-input`: adds frequency-band (bass/mid/treble) analysis per stereo channel + mono.
- `cube-model`: adds spatial region groupings (left/right, top/bottom, front/back).
- `visualization`: adds a cube-aware (region × band) visual and a visual selector; the
  feature set grows to include band energies.

## Impact

- New dependency: `scipy` (Butterworth band filtering for the band envelopes).
- `audio/file.py` gains band envelopes; `audio/source.py` gains `features()`;
  `visuals/base.py` `Features` grows; new `visuals/cube_aware.py`; `cube_model` gains
  region index sets; `app.py`/`cli.py` gain `--visual`. The `(N,3)` color-buffer contract
  is unchanged.
