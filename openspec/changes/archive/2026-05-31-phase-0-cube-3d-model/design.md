## Context

Phase 0 is greenfield. It establishes the data model and the interactive viewer that
every later phase builds on (see [project.md](../../project.md) for the full roadmap and
the physical cube facts). The ground truth is `reference/whole_cube.scad`: a 2.60 m cube
with 2.00 m lit edges and 0.30 m corner cubes carrying X-shaped LED plates.

Hard constraints from the brief: model the LEDs **densely but abstractly** (downstream
MadMapper does real pixel mapping), keep it **portable to desktop** and **low-latency
under heavy compute**, and treat corners as a **denser feature**. The user has chosen a
**Python**, **native-window** stack.

A practical development constraint: the agent building this cannot open an interactive
GPU window in its shell session, so correctness must be provable without a display.

## Goals / Non-Goals

**Goals:**
- A faithful, centered, meters-based cube model with dense abstract LEDs on 12 edges and
  X-panels on 8 corners.
- A stable per-pixel address space and structural regions usable by all later phases.
- A single `(N,3)` RGB color-buffer contract that is the hand-off between visuals and
  rendering.
- An interactive native viewer with orbit-camera exploration at ≥60 FPS.
- A headless self-test + unit tests that prove the data path without a display.

**Non-Goals:**
- No audio, MIDI/F1, DSL, extra surfaces, or MadMapper output (later phases).
- Not modeling individual physical LEDs, real strip wiring, or photometrically accurate
  glow.
- No packaging/installer yet.

## Decisions

### D1 — Rendering stack: moderngl + moderngl-window + numpy
Chosen for full programmable-shader control (needed for the heavy Phase 4 visuals), a
thin native window/input layer, and tiny dependency surface. Alternatives: **VisPy**
(great for point clouds but less low-level shader control), **Panda3D/Ursina** (full game
engines — heavier, more opinionated than we need), **pyglet alone** (more boilerplate for
modern GL). moderngl keeps us close to the GPU with minimal overhead, which matches the
low-latency / high-load requirement.

### D2 — Module layout
```
cube_dance/
  config.py        # CubeConfig dataclass: dims (from SCAD), densities, up-axis
  geometry.py      # structural lines/frames for the 12 edges + 8 corners
  led_topology.py  # dense LED pixel arrays, addressing, region masks -> CubeModel
  patterns.py      # placeholder time-based test pattern (edge sweep + corner pulse)
  render/camera.py # OrbitCamera (numpy view/projection matrices)
  render/scene.py  # moderngl resources + draw(): structure lines + instanced LED points
  app.py           # moderngl-window WindowConfig: wiring + input events + render loop
  selftest.py      # headless data-path validation (no GL)
  cli.py           # entrypoint: launch viewer or --selftest
```
Strict separation of **model** (`config`/`geometry`/`led_topology`, pure numpy, fully
testable headless) from **view** (`render/*`, `app`). Patterns are isolated so Phase 1+
swap them out without touching model or view.

### D3 — CubeModel as flat, index-aligned arrays
`CubeModel` exposes parallel arrays indexed by pixel address `0..N-1`:
- `positions (N,3) float32` — meters, centered, +Y up.
- `group (N,) uint8` — `0=edge`, `1=corner`.
- `element_id (N,) int32` — edge id `0..11` or corner id `0..7`.
- `param (N,) float32` — normalized position along the pixel's structural element (for
  patterns / sweeps).
- `colors (N,3) float32` — the mutable color buffer in `[0,1]`, the write contract.

Region queries are precomputed boolean masks / index lists (`edge_indices[e]`,
`corner_indices[c]`, `group==edge`), so later phases get O(1) vectorised region writes.
Addressing is deterministic: edges first (edge 0..11, each in geometric order), then
corners (0..7), so the same config always yields the same index→pixel mapping.

### D4 — Geometry from SCAD constants, centered, +Y up
Build in SCAD's cm space from the three constants, then convert to meters and translate
to center. Edges: place pixels on the **outer edge line** over `±1.0 m` (reads as the
crisp cube silhouette). Corners: X-shaped (crossed-diagonal) runs on the **3 outward
faces** of each corner plate (the faces whose normal points away from cube center),
within the outer 0.30–0.341 m region. Edge density and corner density are independent
config values; corner density default is higher than edge density.

Defaults: **edges 60 LEDs/m** (≈120 px/edge, matching common WS2812 strips → 1,440 edge
px) and **corners 120 LEDs/m** (≈2.5–3k corner px). Total ≈4k pixels — dense, and trivial
for instanced rendering, leaving GPU headroom for later visuals. All tunable in config.

### D5 — Rendering approach: instanced emissive points + structure lines
LEDs draw as a **single instanced draw call**: one static position VBO + one **dynamic
color VBO** rewritten each frame from `model.colors` via one `buffer.write` (vectorised).
Points render as soft round sprites with **additive blending** to read as glowing LEDs.
The truss structure renders as dim lines (edges) and small corner frames purely for
spatial reference. This satisfies the "batched draw + vectorised per-frame update"
performance requirement.

### D6 — Custom OrbitCamera over moderngl-window camera classes
Implement orbit camera math (azimuth, elevation, distance, target → view matrix; standard
perspective projection) directly with numpy, driven by `mouse_drag_event` /
`mouse_scroll_event` / `key_event`. This avoids coupling to version-specific
moderngl-window camera APIs and keeps behavior identical across backends. Distance is
clamped to min/max bounds so the cube can't be lost.

### D7 — macOS OpenGL specifics
Request a **3.3 core** context and prefer the **glfw** window backend, which reliably
yields a core profile on macOS (OpenGL is deprecated on macOS but 3.3/4.1 remain
available). 3.3 core covers all Phase 0 needs and most later visual work.

### D8 — Provable correctness without a display
The model layer is pure numpy and fully unit-tested (extents, counts, density math,
determinism, partition of regions, buffer contract). A `--selftest` CLI path builds the
model and advances the placeholder pattern for N frames with **no GL/window**. Where the
platform allows, the self-test additionally attempts a best-effort offscreen
`moderngl.create_standalone_context()` shader-compile check, skipping cleanly if no
context is available. The interactive window is then run by the user on their desktop.

### D9 — Placeholder pattern (temporary)
A purely time-based pattern in `patterns.py`: a **hue sweep** travelling along each edge
(driven by `param`) plus a **brightness pulse** on the corners (slow sine), giving
visibly distinct edge-vs-corner behavior to confirm addressing and density. Explicitly
marked temporary; Phase 1 replaces it with audio-driven output writing the same buffer.

## Risks / Trade-offs

- **Cannot interactively test the GPU window in this dev session** → Mitigation: pure-numpy
  model with full unit tests + headless `--selftest` + best-effort offscreen shader check;
  the user launches the interactive window and confirms.
- **macOS OpenGL deprecation** → Mitigation: 3.3/4.1 still ship and cover our needs; if a
  future macOS removes GL, revisit (e.g. wgpu/Metal-backed path). Out of scope now.
- **moderngl-window API drift across versions** → Mitigation: pin a known-good version,
  keep usage minimal, own the camera math.
- **Density too high hurts FPS** → Mitigation: density is config; defaults are dense but
  cheap; single instanced draw scales well past defaults.
- **Corner X geometry is an approximation** → Accepted: the brief says "rough it"; the
  X-on-3-outward-faces reads correctly and is tunable later.

## Migration Plan

Greenfield; no migration. Rollback = revert the change. Establishes the `CubeModel`
color-buffer API that later phases extend rather than replace.

## Open Questions

- Default densities (60/m edges, 120/m corners) and "X on 3 outward faces" are reasonable
  starting points chosen here; revisit once seen on the real cube. Not blocking.
