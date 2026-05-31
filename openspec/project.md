# Project: Cube Dance — LED control software for a truss cube

## Vision

Software that drives the LEDs on a 2.6 m truss cube used at dance-music events. The
lights are **primarily sound-reactive** (the major dynamic element) but **evolve over
time** so a set never looks static. A real-time, interactive **3D simulation** of the
cube is the development substrate and the home for the visual engine. Downstream
"mapping" software (currently **MadMapper**) drives the physical pixels, so the
simulation models LEDs **densely but abstractly** — it is not a model of individual
physical LEDs.

## Physical cube (ground truth)

- Structure: **F34 truss, 2 m sticks**; the cube is **2.6 m per side including the
  corner pieces**.
- Reference CAD: [`reference/whole_cube.scad`](../reference/whole_cube.scad) (OpenSCAD).
  Constants (SCAD units = cm):
  - `stick_height = 200` → **2.00 m** clear LED run per edge
  - `corner_cube_height = 30` → **0.30 m** corner cubes at the 8 vertices
  - `corner_extra_width = 4.1` → corner plates protrude **0.041 m**
  - Cube side = `200 + 2×30 = 260 cm = 2.60 m`
- LEDs:
  - All **12 main edges** of the rectangular prism are lined with LED (straight runs
    ≈ 2 m each). The **internal truss triangles are NOT** lit.
  - The **8 corners** carry their own **X-shaped LED panels** (the truss corner
    plates). They are **denser** and are a deliberate **visual feature** of the cube.

## Coordinate system (simulation)

- Internal units: **meters**. Cube **centered at the origin**; spans `[-1.30, +1.30] m`
  on each axis.
- **+Y is up** (vertical). The cube rests on the floor at `y = -1.30`; 4 bottom corners
  at `y = -1.30`, 4 top corners at `y = +1.30`. `±X` = left/right, `±Z` = front/back.
  This gives clean spatial semantics (L/R, top/bottom, front/back) for later phases.
- Edge LED runs span the central **2.0 m** of each edge (`±1.0 m`) along the outer edge
  line. Corner X-panels occupy the outer **0.30 m** at each vertex, on the outward faces.
- Right-handed.

## Tech stack

- Language / runtime: **Python 3.12**, managed with **`uv`**.
- Rendering: **moderngl** (modern OpenGL) + **moderngl-window** (native window, input,
  GL context). Native desktop app (macOS / Windows / Linux). OpenGL 3.3+ core profile
  (macOS provides up to 4.1).
- Math / data: **numpy**.
- Planned in later phases (do not add before their phase):
  - Audio file decode + analysis (Phase 1/4): `soundfile` / `librosa` (and/or `aubio`).
  - Live audio stream (Phase 6): `sounddevice`.
  - Traktor Kontrol F1 over MIDI (Phase 3): `mido` + `python-rtmidi`.
  - On-screen UI incl. virtual F1 (Phase 3/5): Dear ImGui via `imgui-bundle`.
  - Visual preset config / DSL (Phase 4): YAML or JSON (`PyYAML`).
  - MadMapper output (Phase 8): **Syphon** (macOS) / **NDI** video stream.

## Architecture principles

- **Decouple the pipeline**: (1) cube data model (geometry + LED topology + per-pixel
  color buffer) → (2) renderer / viewer → and, in later phases, (3) audio + MIDI inputs
  → (4) visual generators → (5) output / serialisation. Each stage is replaceable.
- **The LED color buffer is the hand-off contract**: a single `(N, 3)` float RGB array
  indexed by a stable per-pixel address. Visual generators write it; the viewer renders
  it; the Phase 8 output stage serialises it to a video stream for MadMapper.
- **Real-time**: target **60 FPS** with thousands of pixels and heavy visuals. Use
  instanced GPU rendering; keep per-pixel work out of the Python hot path (vectorised
  numpy / shaders).
- **Portability first**: prefer cross-platform APIs; defer native-only APIs (Syphon,
  packaging) until the phase that needs them.

## Phase roadmap (north star — build strictly in order, one OpenSpec change per phase)

Future phases are listed only to convey direction. **Do not build ahead of the current
phase.** Each phase becomes its own change under `openspec/changes/` and is confirmed
complete before the next begins.

- **Phase 0** *(current)*: Interactive, explorable 3D model of the cube with a dense LED
  representation. Foundation for everything else.
- **Phase 1**: Basic musical input from a **loaded audio file**; cube acts as a simple
  **VU meter**.
- **Phase 2**: **Cube-aware** — address corner pieces and beams as **regions** focused in
  the visualisation (e.g. corners = bass L/R, beams = treble).
- **Phase 3**: **Input** — Traktor Kontrol **F1 over MIDI**, plus a **modeled on-screen
  virtual F1** with click-to-input.
- **Phase 4**: Rich, **cube- and music-aware, spatially aware** visualisations that
  **evolve over time** based on the music, driven by a **saveable config / DSL**
  (YAML/JSON).
- **Phase 5**: Map **all F1 controls** to both live control **and** evolution (different
  controls play different roles).
- **Phase 6**: Accept a **live audio input stream** instead of a file.
- **Phase 7**: Optional **"Front of DJ deck"** surface (3 layered LED planes ~2.5 cm
  apart, all crowd-visible — the **origin** of the sound visualisation) and an ambient
  **"projector"** surface. Both optional, toggled by an environment setting.
- **Phase 8**: **Output mode** — serialise surfaces to a video stream for **MadMapper**
  (net surfaces → video → map to physical pixels).

## Conventions

- **Spec-first via OpenSpec.** One change per phase. Capabilities accrete in
  `openspec/specs/` as changes are archived. Run `openspec validate --strict` before
  considering artifacts done.
- Python: `uv run <cmd>`; tests with `pytest`. The OpenSpec CLI itself needs Node ≥ 18.
