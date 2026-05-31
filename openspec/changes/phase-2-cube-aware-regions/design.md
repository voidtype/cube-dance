## Context

`AudioFile` already precomputes a normalised loudness envelope and `level_at(t)`; the
cube model already exposes per-edge / per-corner index sets and per-pixel positions. Phase
2 extends both along the grain that already exists, and adds a visual that combines them.

## Goals / Non-Goals

**Goals:** per-band (bass/mid/treble), per-channel (L/R) audio envelopes; spatial region
sets on the cube; a cube-aware visual (corners = bass L/R, beams = treble/mid) that is
smooth and lightly evolving; a visual selector.

**Non-Goals:** the Phase 4 DSL / saveable evolving presets, beat/tempo tracking, F1
control, live input. Bands are simple fixed-cutoff envelopes.

## Decisions

### D1 — Bands via Butterworth filters + per-hop RMS (scipy)
On load, for the left and right channels, apply three Butterworth band filters
(`sosfiltfilt`): **bass** ≈ 20–200 Hz, **mid** ≈ 200–2000 Hz, **treble** ≈ 2–16 kHz. Take
per-hop RMS of each filtered signal (same hop as the level envelope) → 6 envelopes
(3 bands × L/R) plus mono (channel mean). Normalise each by a high percentile, clip to
`[0,1]`. This is memory-light (no giant STFT) and gives `features_at(t)` by table lookup —
identical for live and offline playback. `AudioSource.features()` returns a `Features` at
the current position.

### D2 — `Features` grows, stays backward-compatible
`Features` gains `bass, mid, treble, bass_l, bass_r` (default 0.0) alongside `level`. The
Phase-1 VU visual ignores the new fields; the cube-aware visual uses them.

### D3 — Spatial regions on the cube model
Add `region_indices`: precomputed pixel-index arrays for `left`/`right` (X<0 / X>0),
`bottom`/`top` (Y), `front`/`back` (Z), derived from `positions`. Combined with the
existing `edge_indices` / `corner_indices` / group masks, visuals can address e.g.
"left corners" = corner pixels with X<0.

### D4 — Cube-aware visual (`spectrum`)
- **Corners = bass, split L/R**: left-corner pixels driven by `bass_l`, right by `bass_r`
  (envelope-followed). Warm hue (red→amber), brightness ∝ band level, with a slow hue
  drift over time (gentle evolution).
- **Beams = mid/treble**: edge pixels brightness ∝ a mix of `mid`+`treble`, cooler hue
  (cyan→blue→violet), with treble adding a brighter top end. Optional faint sparkle.
- All writes are vectorised over the precomputed region index sets; per-band envelope
  followers (fast attack / slower release) keep it smooth.

### D5 — Visual selection
`--visual {auto,spectrum,vu}` (default `auto`). `auto` = `spectrum` when an audio source
exists, else the placeholder pattern. The app builds the chosen visual; HUD shows it.

## Risks / Trade-offs

- **Fixed band cutoffs** won't suit every track → acceptable for Phase 2; per-track gain
  normalisation already helps. Tunable later.
- **`sosfiltfilt` on long files** adds a little load-time cost → one-off on load, fine.
- **Headless verification**: bands + visual are pure numpy/scipy and unit-tested; the
  look is checked via offscreen renders.

## Open Questions

- Exact band→hue mapping is chosen by eye here (bass=warm corners, treble=cool beams) and
  is easy to retune; Phase 4 will make this configurable.
