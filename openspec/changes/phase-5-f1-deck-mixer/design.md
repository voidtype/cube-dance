## Context

Phase 4 `VisualEngine.update(model, t, features)` advances evolution, builds a `Context`, and
composites elements into `model.colors` (then applies `master` + clip). Phase 5 needs N of
these running at once and blended by per-deck volume, plus the F1 controls wired to both
performance (volumes, preset choice) and evolution (global modulators).

## Decisions

### Deck mixer over a single engine

- `DeckMixer` holds `n_decks=4` `VisualEngine`s that **share one `VisualParams`** (knobs are
  global) but keep **independent evolution + element state** (so layered decks differ).
- Blend is **additive then clipped**, each deck weighted by its fader volume. Additive
  matches the existing element compositing and reads well for "fade a layer in".
- Only decks with `volume > ~0.005` are rendered each frame (perf). A muted deck's internal
  state simply pauses until it is faded back in — imperceptible on fade-in.

### Engine render/update split

- Add `VisualEngine.render(model, t, features, out)`: advance evolution (honoring `freeze`),
  build the `Context` (now carrying `intensity`/`size`/`mono`), composite elements into
  `out`, and multiply by `intensity`. **No `master`, no clip** — the caller owns those.
- `update(...)` becomes `render(model, t, features, model.colors)` then `*= master`, clip —
  so the standalone path (selftest, unit tests) is unchanged.
- The mixer renders each deck into a scratch buffer and accumulates `+= scratch * volume`,
  then `*= master`, clip, into `model.colors`.

### Focus + preset selection

- `ControlState.focus_deck` (0..3) is set by the **fader you touch** (virtual panel + MIDI).
- The mixer owns `preset_index[deck]` against an ordered `PRESET_ORDER`. The app each frame:
  on focus change, mirror `controls.p` to the focused deck's index (so the display tracks the
  deck); then `target = p % len(order)`, write `p = target` (keeps the 7-seg in range), and
  if it differs `mixer.set_deck_preset(focus, order[target])` (rebuilds that deck's elements).
- `N` bumps `controls.p` (cycles the focused deck's preset). This unifies "P selects preset"
  and "key cycles preset" onto the same per-deck mechanism.

### Control roles (global modulators)

`ControlMap.apply` stops touching faders (the mixer reads them as volumes) and the encoder
(it selects presets). Knobs → `VisualParams`: `intensity` (0.3–1.7), evolution speed
(`hue_drift_base` 0–0.05 with `REVERSE` sign + `hue_accel_per_min` 0–3), `size` (0.5–1.8,
×1.5 when `SIZE`), and AGC `presence_gamma` (hide-quiet). Buttons set flags: `SHIFT`→`freeze`,
`TYPE`→`mono`. Elements read `ctx.size`/`ctx.mono`; `intensity`/`freeze` act in the engine.

### Element modulator honoring

- `intensity` is applied once in the engine (global gain) — no per-element edits.
- `mono` sets saturation to 0 wherever an element builds colour (stark white look — the user
  asked for starkness).
- `size` scales spatial extent: `Sweep`/`Chase` width, `HatSparkle` count, `AmbientWash`
  spread. Frequency/bass/kick elements ignore size (size is about spatial spread).

## Risks / Trade-offs

- **4× compute.** Worst case all decks audible → ~4× element work. Measured single engine
  ~1.9 ms/frame headless; 4× ≈ 7.6 ms (~130 fps) — fine. Muted-deck skip keeps the common
  case (1–2 decks up) cheap.
- **Focus ambiguity on MIDI** (no "touch" until a fader moves): default focus 0; any fader CC
  sets focus. Acceptable; a dedicated focus control can come with the mapping editor later.
- **Shared params across decks** means a knob affects every deck. That's the intent (global
  feel); per-deck params would need a deck-select modifier — deferred.
