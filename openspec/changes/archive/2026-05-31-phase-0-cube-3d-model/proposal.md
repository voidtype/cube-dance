## Why

Every later phase (audio reactivity, cube-aware regions, F1 control, evolving visuals,
MadMapper output) writes to or reads from a single shared model of the cube's LEDs and
needs to be seen while developing. Phase 0 builds that foundation: a faithful, dense,
**interactive 3D simulation** of the 2.6 m truss cube and the **LED color-buffer
contract** that the rest of the system is built around. Nothing downstream can be
designed or trusted until we can explore the cube and watch its pixels light up.

## What Changes

- Add a **cube data model** derived from `reference/whole_cube.scad`: the 12 lit edges
  and 8 corner X-panels, expressed as a **dense set of abstract LED pixels** (not
  individual physical LEDs) with positions in meters, centered at the origin.
- Define a **stable per-pixel addressing scheme** and **structural regions** (per-edge,
  per-corner, and edges-vs-corners groupings) so later phases can target the cube
  spatially without re-deriving geometry.
- Establish the **LED color buffer contract**: a single `(N, 3)` float-RGB array that
  visual generators write and the viewer renders — the hand-off used by every later
  phase, including the Phase 8 serialiser.
- Add an **interactive native 3D viewer** (moderngl + moderngl-window): renders the
  truss structure plus the LED pixels as emissive points, with an **orbit camera**
  (drag to rotate, scroll to zoom, pan) for free exploration, targeting 60 FPS with
  thousands of pixels.
- Add a **placeholder, non-audio test pattern** that animates the color buffer over
  time (edge sweep + corner pulse) purely to validate density, addressing, and the
  buffer→render pipeline. This is explicitly temporary scaffolding for later phases.
- Add a **headless self-test / data path** so the model and buffer pipeline can be
  validated without a display (the interactive window requires the user's GPU/desktop).
- Configurable **LED density** (LEDs per meter) with a dense default, plus denser
  corners, satisfying "make your simulation dense."

Post-review refinements (still Phase 0): model the truss beams as square sections lit
with **2 rows per visible face** (chords), with **base edges** lighting only their
outward vertical face; light the **corner cubes on their edges** (glowing outline) plus
the X panels; add **optional realism scenery** (floor + speaker cabinets); and provide
**two navigation modes** (orbit and fly/FPS) with an on-screen help overlay.

Explicitly **out of scope** for Phase 0: any audio, MIDI/F1 input, the visual DSL,
extra surfaces, and MadMapper output. Those are later phases.

## Capabilities

### New Capabilities
- `cube-model`: The physical cube geometry, the dense abstract LED topology (edge runs +
  corner X-panels), the stable per-pixel addressing and structural regions, and the
  shared `(N, 3)` RGB color-buffer contract.
- `simulation-viewer`: The interactive native 3D viewer — render loop, structure + LED
  rendering, orbit-camera exploration, the placeholder test pattern, and the headless
  self-test path.

### Modified Capabilities
<!-- None — this is the first change; no existing specs. -->

## Impact

- New Python package `cube_dance/` (managed by `uv`): geometry, LED topology, viewer,
  app entrypoint.
- New dependencies: `moderngl`, `moderngl-window`, `numpy` (plus `glfw` window backend
  on macOS). Dev: `pytest`.
- New runnable entrypoint (e.g. `uv run cube-dance`) launching the interactive window;
  a `--selftest` flag for the headless data-path check.
- Establishes the color-buffer API that Phases 1–8 depend on; later phases extend, not
  replace, these two capabilities.
