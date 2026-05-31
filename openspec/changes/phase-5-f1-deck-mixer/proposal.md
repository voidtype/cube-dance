## Why

Phase 4 gave us a preset-driven element engine, but only one preset plays at a time and the
F1 still maps onto a few global params. Phase 5 makes the **F1 the live instrument** for the
new architecture: every control either **performs** the show or **shapes its evolution**.
The headline is a **4-deck mixer** — a preset "plays" on each fader and the fader is that
deck's **volume**, so you blend presets live like a VJ mixer. The **P encoder selects the
preset** for the deck you're working, and the knobs/buttons reach **into the presets**
(intensity, evolution speed, size, stark/mono, freeze).

## What Changes

- **4-deck preset mixer.** The default `spectrum` visual becomes a `DeckMixer` of **4 decks**,
  each an independent element-engine running a preset with its own evolution state. Each
  deck's **fader is its volume**; the blended (additive, clipped) result drives the cube.
  Decks share one set of global params (the knobs), so the knobs are "global feel" and the
  faders are "per-deck level". Default decks: `deep`, `punchy`, `minimal`, `strobe` (only
  deck 1 up at launch).
- **P encoder selects the focused deck's preset (runtime).** The deck you last touched (its
  fader) is **focused**; scrolling the **browse encoder** cycles that deck's preset through
  the built-in list, shown on the **7-segment display**. `N` does the same from the keyboard.
- **More controls reach into the presets.** Knobs become global modulators every element
  honors: **intensity**, **evolution speed** (hue drift + acceleration, `REVERSE` flips
  direction), **size** (sweep/chase width, sparkle count), **hide-quiet** (AGC presence).
  Buttons: `SHIFT` = **freeze** evolution (hold the palette), `TYPE` = **mono/stark**
  (desaturate to white), `SIZE` = **fat** boost. Pads keep the manual accent flash.
- **Two new presets** to fill the decks: `minimal` (calm beams + bass, no flashes) and
  `strobe` (hard white kicks + dense sparkle).
- **Engine split** so decks compose cheaply: `VisualEngine.render(model, t, features, out)`
  composites into a given buffer (no master/clip); `update(...)` keeps the standalone path.

Out of scope (later phases): hot-reload of preset files, MIDI mapping editor, live audio
input (Phase 6), extra surfaces (Phase 7), MadMapper output (Phase 8).

## Impact

- Specs: `control-input` (knob/fader/encoder/button roles redefined; deck focus),
  `visual-engine` (deck mixer + global modulators + render split), `preset-system` (preset
  list / built-ins for decks), `virtual-f1` (per-deck volume faders, preset display, focus).
- Code: new `visuals/engine/mixer.py`; `params.py`, `context.py`, `engine.py`, `elements.py`,
  `presets/` (+`minimal`,`strobe`), `control/{state,mapping,midi}.py`, `render/virtual_f1.py`,
  `app.py`, `cli.py`, tests.
- The `(N,3)` buffer hand-off is unchanged; `vu` and the placeholder remain.
