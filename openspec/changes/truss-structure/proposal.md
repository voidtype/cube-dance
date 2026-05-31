## Why

The LEDs currently float in space with nothing under them. On the real rig the LED strips
are mounted **on the F34 truss**, so the simulation should model the truss beneath the
lights — both for realism and so the LEDs visibly sit *on* a structure.

## What Changes

- Add **truss structural geometry** derived from the F34 box truss: per edge beam, the
  **4 chords** (the tubes the LED rows sit on) plus **diagonal lacing** (the triangles) on
  the visible faces; and per corner, the **corner-cube frame** (its 12 edges) plus X
  bracing. Built as tubes (cylinders), in metres, aligned so the existing LED chords lie on
  the chord tubes.
- Add a **per-pixel outward orientation** (normal) to the cube model so LEDs can be nudged
  onto the outer surface of their tube (lights *on top of* the truss, not buried in it).
- Render the truss as **dull aluminium**: a metallic grey that reacts to light (diffuse +
  a soft, low specular highlight), drawn **opaque beneath the additive LEDs** so the truss
  occludes correctly while the LEDs glow on top.
- Toggle with **`--no-truss`** (default on).

Not aiming for a photoreal truss — a believable dull-metal frame with chords, lacing and
corner blocks. Triangles are included (F34 lacing) on the outward faces.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `cube-model`: adds truss structural geometry (chords, lacing, corner frames) and a
  per-pixel outward normal.
- `simulation-viewer`: renders the truss as dull aluminium beneath the LEDs, with the LEDs
  offset onto the tube surfaces.

## Impact

- New module `cube_dance/truss.py` (tube/cylinder mesh from the existing edge/corner
  geometry); `led_topology` gains a `normal` array; `render/scene.py` gains a metal shader
  + truss draw and offsets the LED positions; `config`/`cli` gain a truss toggle.
- No change to the audio path or the `(N,3)` color-buffer contract.
