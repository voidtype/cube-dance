## 1. Engine: global modulators + render split

- [x] 1.1 `visuals/params.py`: add `intensity`, `size`, `freeze`, `mono` to `VisualParams`.
- [x] 1.2 `visuals/engine/context.py`: `Context` carries `intensity`, `size`, `mono`.
- [x] 1.3 `visuals/engine/engine.py`: `render(model, t, features, out)` (composite into `out`,
      honor `freeze`, apply `intensity`, no master/clip); `update` = `render`→`*master`→clip.
- [x] 1.4 `visuals/engine/elements.py`: honor `ctx.mono` (sat→0) and `ctx.size`
      (Sweep/Chase width, HatSparkle count, AmbientWash spread).

## 2. Deck mixer + presets

- [x] 2.1 `visuals/engine/mixer.py`: `DeckMixer` (4 shared-params decks, per-deck volume +
      preset_index, additive blend + master/clip, render only audible decks, `set_deck_preset`).
- [x] 2.2 `presets/__init__.py`: ordered `PRESET_ORDER` (deep, punchy, minimal, strobe).
- [x] 2.3 `presets/minimal.py` + `presets/strobe.py`.

## 3. Controls → mixer + modulators

- [x] 3.1 `control/state.py`: `focus_deck`; default faders `[0.85, 0, 0, 0]`.
- [x] 3.2 `control/mapping.py`: knobs → intensity/evolution/size/hide-quiet; buttons →
      reverse/freeze/mono/size; stop mapping faders + encoder.
- [x] 3.3 `control/midi.py`: a fader CC sets `focus_deck`.

## 4. F1 panel + app wiring

- [x] 4.1 `render/virtual_f1.py`: fader touch sets `focus_deck`; render per-deck preset labels
      + focus highlight; updated knob roles; "PRESET" hint by the display.
- [x] 4.2 `app.py`: build `DeckMixer`; per frame set deck volumes from faders, resolve focus +
      `p`→focused deck preset; `N` bumps the focused deck's preset; pass deck labels+focus to F1.
- [x] 4.3 `cli.py`: `--preset` sets deck 1's starting preset (others keep defaults).

## 5. Verify & document

- [x] 5.1 `tests/test_phase5.py`: mixer blends by volume; `set_deck_preset` swaps elements;
      intensity/mono/size/freeze affect output; `PRESET_ORDER` wraps; ControlMap maps knobs;
      virtual-F1 fader touch sets focus.
- [x] 5.2 `uv run pytest` green; `--selftest --demo` ok; offscreen renders of a blend + mono.
- [x] 5.3 Update `README.md` (deck mixer, fader volumes, P preset select, control roles).
- [x] 5.4 `openspec validate phase-5-f1-deck-mixer --strict` passes.
