## Context

The visuals are driven by `VisualParams`/`AgcParams`. Phase 3 adds a control surface (real
F1 and/or a virtual one) that writes those params. The viewer already has a Pillow→texture
HUD and mouse/keyboard events, and two camera modes (fly captures the mouse).

## Goals / Non-Goals

**Goals:** an interactive virtual F1 (draggable knobs/faders, click-to-light buttons,
digital P display + scroll encoder, pads), a control→param mapping, basic F1 MIDI input, and
a `C` toggle that releases the mouse + freezes movement while the panel is up.

**Non-Goals:** the full Phase-5 control/evolution mapping + DSL, per-pad behaviour, MIDI
output/LED feedback to the hardware, live audio (Phase 6).

## Decisions

### D1 — Control model + mapping (hardware-agnostic)
`ControlState`: `knobs[4]`, `faders[4]` (0..1), `buttons{name: bool}`, `encoder` / `p`
(0..99 display), `pads[16]`. A `ControlMap` applies the state to `VisualParams`/`AgcParams`
each frame (knobs/faders → continuous params, encoder → `p` → a hue offset, buttons →
toggles). Both the virtual panel and MIDI write `ControlState`, so they're interchangeable.

### D2 — Virtual F1 rendered with Pillow, redraw-on-change
The panel is drawn to a texture with Pillow (rounded-rect buttons, knob dial with an
indicator, fader track+handle, a 7-segment P display, coloured pads), modelled on the real
layout, placed in the **right quarter**. It re-renders only when state changes (drag/click/
scroll) — cheap when idle. Hit-testing uses widget rects in screen space.

### D3 — Interaction
While the overlay is open the app routes mouse to the panel: a knob/fader hit starts a drag
(vertical drag delta → value, VST-style); a button hit toggles + relights; scroll over the
encoder changes `p`. `C` toggles the overlay and, when shown, sets `mouse_exclusivity=False`
and a `frozen` flag (camera/WASD ignore input) so the cursor controls the panel. Closing
restores the previous nav mode.

### D4 — Basic MIDI (guarded, optional)
A `MidiInput` opens the first Traktor F1 input port via `mido` (lazy, background, guarded —
like the audio device). Incoming CC → knobs/faders, notes → buttons; it writes the same
`ControlState`. Absent hardware it's a no-op. Exact CC/note numbers are configurable later
(Phase 5); a sensible default map is used now.

### D5 — `master` brightness
`VisualParams.master` (0..1.5) multiplies the visual's output so a fader has an obvious
global effect; applied in the cube-aware visual.

## Risks / Trade-offs

- **Pillow redraw cost while dragging** → only redraw on change; panel is small. Fine.
- **No F1 hardware here to test MIDI** → the MIDI path is guarded/optional and structured;
  the virtual panel (fully testable) is the primary surface. Mapping + interaction are unit-
  tested; the panel is checked via offscreen render and a hidden-window toggle smoke.
- **Hit-testing accuracy** → widget rects are derived from the same layout used to draw, so
  they stay in sync.

## Open Questions

- The specific knob/fader→param assignment is chosen by eye ("relevant params for now");
  Phase 5 formalises control + evolution roles, likely via the DSL.
