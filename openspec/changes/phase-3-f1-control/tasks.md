## 1. Control model + mapping

- [x] 1.1 `control/state.py`: `ControlState` — knobs[4], faders[4], buttons{}, encoder/p (0..99), pads[16]; default values; `step_encoder(delta)` wrapping P.
- [x] 1.2 `control/mapping.py`: `ControlMap` — apply `ControlState` to `VisualParams`/`AgcParams` (knobs/faders → continuous params, P → hue offset, buttons → toggles). Named knob/fader roles.
- [x] 1.3 `visuals/params.py`: add `master` brightness; apply it in `CubeAwareVisual`.

## 2. Virtual F1 panel

- [x] 2.1 `render/virtual_f1.py`: layout (right-quarter rects for knobs/faders/buttons/display/encoder/pads) + Pillow render (knob dials, fader tracks+handles, rounded buttons grey/lit, 7-seg P display, coloured pads); redraw-on-change to a texture; draw as an overlay quad.
- [x] 2.2 `render/virtual_f1.py`: hit-testing + interaction — `on_press(x,y)`, `on_drag(dx,dy)`, `on_release()`, `on_scroll(x,y,dir)`; map drags to knob/fader values, clicks to button toggles, scroll over the encoder to P; write `ControlState`; mark dirty.

## 3. Viewer integration

- [x] 3.1 `app.py`: build `ControlState` + `ControlMap` + `VirtualF1`; apply the mapping each frame.
- [x] 3.2 `app.py`: `C` toggles the overlay; while shown release the mouse + set a `frozen` flag (camera/WASD ignore input); route mouse press/drag/release/scroll to the panel; restore nav on close.

## 4. MIDI (basic, guarded)

- [x] 4.1 Add `mido` + `python-rtmidi` via `uv add`.
- [x] 4.2 `control/midi.py`: `MidiInput` — find a Traktor F1 port (lazy/guarded), map CC→knobs/faders and notes→buttons into the shared `ControlState`; no-op if absent.

## 5. Verify & document

- [x] 5.1 `tests/`: mapping (knob→param, encoder→P wrap, button toggle); `VirtualF1` interaction (drag knob changes value; click toggles+lights; scroll changes P); `master` affects output.
- [x] 5.2 `uv run pytest` green; offscreen render the panel (default + some lit buttons); hidden-window smoke for the `C` toggle (overlay shows, mouse released, frozen).
- [x] 5.3 Update `README.md` (C overlay, the virtual F1, control mapping, MIDI note).
- [x] 5.4 `openspec validate phase-3-f1-control --strict` passes.
