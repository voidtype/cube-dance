## Context

Phase 0 established `CubeModel.colors` (an `(N,3)` buffer) and a viewer that renders it.
Phase 1 introduces the first writer driven by sound. The hard constraint from the dev
environment carries over: the agent cannot use an audio output device or interactive
window in its shell, so the **analysis and visual logic must be testable offline**, with
device playback as a thin, gracefully-degrading layer on top.

## Goals / Non-Goals

**Goals:**
- Load an audio file, derive a normalised loudness level at any position.
- A transport (play/pause/restart/seek) and audio playback synced to the visuals, with a
  silent fallback when no device exists.
- A visualisation layer writing the color buffer; one VU-meter visual for Phase 1.
- A `--demo` synth so it runs with no file; all analysis/visual logic unit-tested offline.

**Non-Goals:**
- Spatial / cube-aware mapping (Phase 2), frequency bands, MIDI (Phase 3), the visual DSL
  (Phase 4), live input streams (Phase 6). Phase 1 is **mono, global loudness**.

## Decisions

### D1 — Decode with `soundfile`, analyse with numpy
`soundfile` (libsndfile) decodes WAV/FLAC/AIFF/OGG into a numpy array; we load the whole
file (DJ tracks are minutes — trivial in RAM) and keep a mono mix (channel mean).
Alternatives: `librosa` (heavier, pulls numba), `pydub` (needs ffmpeg). We only need
decode + RMS, so `soundfile` + numpy is the lean choice. `AudioFile.from_array` allows
constructing from a numpy array (used by the demo synth and tests).

### D2 — Loudness envelope (per-hop RMS), normalised
Compute RMS over fixed hops (default 512 samples ≈ 11.6 ms @ 44.1 kHz) on the mono mix.
Normalise by a **high percentile** (99th) of the hop RMS so a single transient doesn't
crush the scale, then clip to `[0,1]`. `level_at(t)` indexes the hop at `t` (clamped). This
is cheap, deterministic, and identical for live and offline playback.

### D3 — `AudioSource`: transport + clock with two modes
`AudioSource` owns the `AudioFile`, the transport state (`playing`, `position`), and an
optional playback stream. Two clock modes:
- **live**: a `sounddevice.OutputStream` callback copies `samples[frame:frame+n]` to the
  device and advances `frame`; `position = frame / sr`.
- **virtual** (no device / muted): `position` advances by the `dt` passed to `update()`.
`play/pause/restart/seek` work in both modes (live seek = set the callback's frame index).
`level()` = `AudioFile.level_at(position)`. This keeps visuals correct whether or not
sound plays.

### D4 — Playback via `sounddevice`, lazy + guarded
`sounddevice` (PortAudio) is imported lazily inside `AudioSource.start()` and wrapped in
`try/except`; any failure (no device, import error) or `--mute` falls back to the virtual
clock. So headless/CI and the offline self-test never touch the device.

### D5 — Visualisation layer
A small `Visual` protocol: `update(model, t, features)` writes `model.colors`. `features`
is a lightweight dict/struct (Phase 1: `{level}`; later phases add bands/regions).
`PlaceholderVisual` wraps the Phase 0 pattern. `VuMeter` implements the meter. The app
picks `VuMeter` when an audio source exists, else `PlaceholderVisual`. This is the seam
Phase 4 expands into the full visual engine/DSL.

### D6 — VU meter mapping
Per pixel, normalised height `h = (y + half) / side ∈ [0,1]`. The displayed level is an
**envelope follower** over the input level — fast attack, slower release:
`disp += (level - disp) * (attack if level>disp else release)`. A pixel is **lit if
`h ≤ disp`**, coloured on a green→amber→red ramp by `h`, brightness scaled by the level;
pixels above are off. A thin **peak-hold** band is drawn at a separately-decaying peak
height. Vectorised over all pixels (no per-pixel Python).

### D7 — Demo synth
`--demo` synthesises ~8 s of 4-on-the-floor at 120 BPM: a decaying ~60 Hz sine kick with a
click transient on each beat plus short noise hats on off-beats, 44.1 kHz stereo,
deterministic. Gives obvious VU pulsing with no external file.

### D8 — Keys & HUD
Transport keys independent of nav mode: **`K`** play/pause, **`J`** restart. When audio is
active the HUD shows `position / duration` and play state; with no audio, `P` still
pauses the placeholder (Phase 0 behaviour). The viewer otherwise is unchanged.

## Risks / Trade-offs

- **Cannot test real device playback here** → Mitigation: virtual-clock fallback path is
  fully tested; analysis + VU are pure-numpy tested; the user verifies sound on their Mac.
- **Audio/visual drift** if visuals used wall-clock while sound used the audio clock →
  Mitigation: in live mode the visual position is derived from the audio stream frame
  counter, so they cannot drift.
- **MP3** support depends on the bundled libsndfile version → Accept for Phase 1 (document
  WAV/FLAC/AIFF/OGG); a decode fallback can come later if needed.
- **Envelope normalisation** by a fixed percentile may differ per track → acceptable for a
  "simple" VU; per-track auto-gain/AGC is a later refinement.

## Migration Plan

Additive. No changes to geometry or renderer; the placeholder remains the no-audio
default. Rollback = revert the change.

## Open Questions

- Default VU look (mono vertical fill, green→amber→red, peak-hold) is chosen here as the
  "simple" meter; spatial/stereo behaviour is deliberately deferred to Phase 2.
