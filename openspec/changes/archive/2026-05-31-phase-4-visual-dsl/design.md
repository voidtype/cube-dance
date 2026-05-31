## Context

Phase 2 gave us a streaming `SpectrumAnalyzer` (per-window per-channel buckets) and an AGC.
Phase 4 builds on the same window: an **event-detection** layer (classified transients +
bass envelope) and a **Python element engine** that consumes events + features. Everything
stays streaming (file or live) and heuristic (sub-10 ms DSP, no precompute, no ML yet).

## Goals / Non-Goals

**Goals:** classified drum events (kick/snare/hat/perc) + a sustained bass stream; a
composable, event-subscribing Python element engine; beat/energy-driven evolution + light
composition awareness; a Python preset system; keep it real-time.

**Non-Goals:** stem separation, ML classification, full transcription, hot-reload/F1 roles
(Phase 5), live input device (Phase 6).

## Decisions

### D1 — Two-stream event detector (heuristics)
`audio/events.py`: from the STFT window, compute **per-band spectral flux**; a band onset
fires when flux exceeds a moving-average threshold (per-band, with refractory time).
Per onset, extract features (dominant band, spectral centroid, flatness, energy) and
**classify**: low + sharp → `kick`; high + noisy (high flatness/centroid) → `hat`; broadband
mid → `snare`; else `perc`. Separately, an **envelope follower** on the sub band (30–120 Hz)
gives a continuous `bass` value (+ d/dt). **Kick vs bass**: a sub-band onset with a sharp,
short attack is a kick *event*; sustained sub energy is the bass *level*. Per-class window
length differs (hats short, kick/snare longer). Output each frame: `events: list[Event]`
that fired + continuous features.

### D2 — Element engine + context (Python)
`visuals/engine/`: a `Context` carries `events`, continuous `features`, `beat` phase, `t`,
`dt`, and the `CubeModel`. An `Element` has `update(ctx)` and writes into a scratch buffer
with a **blend** (add/max/over) and a **region** mask + **palette**. The `VisualEngine`
runs elements in order, composites into `model.colors`, and exposes the shared context.
Elements **subscribe** to event classes (a fired event triggers an internal envelope) and
to continuous streams. Built-in elements: `BassCorners`, `SpectrumBeams`, `KickPulse`,
`HatSparkle`, `Sweep`, `Chase`, `AmbientWash`. **Modulators** (LFO / feature-envelope /
time-evolver) drive element params; an evolver's rate can **accelerate** over time.

### D3 — Composition awareness + evolution
A small `Composition` tracker integrates energy and onset density to estimate an
intensity/section state and detect build-ups/drops (energy + density slope). Evolution: an
energy accumulator advances a global phase; palettes rotate and element intensities grow
with it, and drift accelerates over the set, so long sets keep changing.

### D4 — Python preset system
`presets/<name>.py` exposes `build(engine)` that adds elements + wires subscriptions /
modulators (Python = full expressiveness, matches the requested "subscribe + element
abstraction"). A loader imports by name; built-ins ship in the package; `--preset` selects.
(Sandboxed hot-reload is deferred; presets are trusted code for now.)

### D5 — Beat/tempo
Onset times feed a lightweight inter-onset-interval tempo/phase estimate so `beat` phase is
available to elements (pulses, tempo-locked sweeps). Rough is fine for lighting.

## Risks / Trade-offs

- **Full-mix confusion** (midrange snare vs synth) → lean on frequency extremes; midrange is
  best-effort; classifier upgrade path kept open.
- **Scope** → build in layers: event detector (tested on synthetic kick/hat) → engine + a
  few elements → preset + integration → evolution. Each lands runnable.
- **Headless verification** → events tested on synthesised kick/hat/bass; engine/elements
  unit-tested by feeding a context; the look checked via offscreen renders.

## Open Questions

- Exact classification thresholds + per-class windows are tuned empirically; defaults now,
  refine on real tracks (and via the F1 in Phase 5).
