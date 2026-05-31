## Why

The visuals need hands-on control. Phase 3 introduces an **input layer** targeting the
**Traktor Kontrol F1**, and — so it works with no hardware and is easy to develop against —
an **on-screen virtual F1** you can click and drag. Controls map to the visual/AGC params
we already exposed (the hooks for the Phase-4 DSL).

## What Changes

- Add a **control model**: the F1's controls as state — 4 **FILTER knobs**, 4 **faders**,
  the function **buttons** (SYNC/QUANT/CAPTURE, SHIFT, REVERSE/TYPE/SIZE/BROWSE), a **browse
  encoder**, a 2-digit **display value (P)**, and the 4×4 **pads** — plus a **mapping** from
  controls to `VisualParams`/`AgcParams` (knobs/faders → continuous params, encoder → the P
  display, buttons → toggles). "Relevant params for now"; the full mapping + evolution roles
  come in Phase 5.
- Add an **on-screen virtual F1** overlay, modelled on the real unit, in the **right
  quarter** of the window:
  - **Knobs and faders are click-and-drag** widgets (drag to change, VST-style).
  - **Buttons are grey by default and light up when clicked.**
  - A **digital (7-segment) display** shows **P**; **scrolling over the encoder** next to it
    changes P.
  - The 4×4 **pads** are shown (lit), styled like the unit.
- **`C` toggles the controls overlay.** While it is shown the viewer **releases the mouse
  (detaches fly-look) and freezes camera movement**, so the cursor drives the panel.
- Add **basic MIDI input**: if a Traktor F1 is connected, its messages feed the same control
  model (knobs/faders/buttons), so hardware and the virtual panel are interchangeable.

Out of scope (later): the full per-control evolution roles + DSL (Phase 5), live audio input
(Phase 6). Pads are display-only for now (no per-pad function yet).

## Capabilities

### New Capabilities
- `control-input`: the F1 control model, the control→param mapping, and basic Traktor F1
  MIDI input feeding it.
- `virtual-f1`: the interactive on-screen F1 panel (right-quarter overlay) with draggable
  knobs/faders, click-to-light buttons, a digital P display + scroll encoder, and pads.

### Modified Capabilities
- `simulation-viewer`: `C` toggles the controls overlay; while shown the mouse is released
  and navigation is frozen.

## Impact

- New deps: `mido` + `python-rtmidi` (MIDI). New `cube_dance/control/` (state, mapping, midi)
  and `cube_dance/render/virtual_f1.py` (the panel). `app.py` gains the `C` toggle, the
  freeze/mouse-release, mouse routing to the panel, and applies the mapping each frame.
  `VisualParams` gains a `master` brightness. The `(N,3)` buffer contract is unchanged.
