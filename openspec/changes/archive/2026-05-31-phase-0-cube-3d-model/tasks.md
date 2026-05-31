## 1. Project setup

- [x] 1.1 Configure `pyproject.toml`: package `cube_dance`, deps (`moderngl`, `moderngl-window`, `numpy`, `glfw`), dev deps (`pytest`), and a `cube-dance` console script; pin known-good versions via `uv add`.
- [x] 1.2 Create the package skeleton: `cube_dance/{__init__,config,geometry,led_topology,patterns,selftest,cli}.py` and `cube_dance/render/{__init__,camera,scene}.py`.
- [x] 1.3 Remove the uv-generated `main.py`; wire the `cube-dance` entrypoint to `cube_dance.cli:main`.

## 2. Cube model (pure numpy, headless-testable)

- [x] 2.1 `config.py`: `CubeConfig` dataclass with SCAD-derived dimensions (2.60 m side, 2.00 m edge run, 0.30 m corner, 0.041 m plate), edge/corner LED densities (defaults 60 and 120 LEDs/m), and up-axis = +Y.
- [x] 2.2 `geometry.py`: derive the 12 edge segments (outer edge lines, ±1.0 m span) and 8 corner plates (with their 3 outward faces) in centered meters, +Y up; expose counts and extents.
- [x] 2.3 `led_topology.py`: build dense, evenly spaced edge pixels along each edge's outer line at edge density (`round(D×2.0)` per edge).
- [x] 2.4 `led_topology.py`: build corner X-panel pixels as crossed diagonals on each corner's 3 outward faces at corner density (strictly denser than edges).
- [x] 2.5 `led_topology.py`: assemble `CubeModel` — index-aligned `positions/group/element_id/param/colors` arrays, deterministic addressing (edges 0..11 then corners 0..7), and precomputed region masks/index lists; `colors` is `(N,3)` float in `[0,1]` initialised to zeros.
- [x] 2.6 `geometry.py`: produce structure line geometry (edge lines + corner frames) for the viewer's spatial reference.

## 3. Placeholder pattern

- [x] 3.1 `patterns.py`: time-based placeholder writing `model.colors` vectorised — a hue sweep travelling along edges (via `param`) plus a corner brightness pulse; clearly documented as temporary scaffolding replaced in Phase 1.

## 4. Rendering & interactive viewer

- [x] 4.1 `render/camera.py`: `OrbitCamera` (azimuth/elevation/distance/target → view matrix, perspective projection) with distance clamped to min/max bounds.
- [x] 4.2 `render/scene.py`: moderngl resources — a single instanced LED draw (static position VBO + dynamic color VBO) with soft round sprites and additive blending, plus dim structure lines; `update_colors()` rewrites the color VBO from `model.colors` in one `buffer.write`.
- [x] 4.3 `app.py`: `moderngl-window` `WindowConfig` (GL 3.3 core, glfw backend) wiring model + camera + scene + pattern; per-frame loop advances pattern → buffer → scene; show FPS in the window title.
- [x] 4.4 `app.py`: input handling — mouse drag to orbit, scroll to zoom (clamped), pan, and key bindings (reset view, quit); print the controls to the console on launch.
- [x] 4.5 `cli.py`: entrypoint parsing (`--selftest`, `--frames N`, density overrides); launch the interactive viewer or the headless self-test.

## 5. Headless self-test & unit tests

- [x] 5.1 `selftest.py`: build the model, advance the pattern N frames with no GL/window, print pixel count + buffer shape + timing, attempt a best-effort offscreen `create_standalone_context()` shader-compile check (skip cleanly if unavailable), and exit 0.
- [x] 5.2 `tests/`: unit tests for geometry (extents ±1 mm, 12 edges / 8 corners), topology (edge count `= 12×round(D×2)`, edge pixels on-line within 1 mm and within ±1.0 m, corners strictly denser, X runs present per corner), addressing (deterministic across builds, contiguous `0..N-1`), regions (each pixel exactly one element; regions partition the set), and color buffer (shape `(N,3)`, zero-init, addressable write).
- [x] 5.3 `tests/`: self-test smoke test — runs, exits 0, opens no window.

## 6. Verify & document

- [x] 6.1 Run `uv run pytest` and `uv run cube-dance --selftest`; ensure both pass green.
- [x] 6.2 Write `README.md`: how to launch (`uv run cube-dance`), camera/key controls, the `--selftest` and density flags, and the macOS GL/glfw note.
- [x] 6.3 `openspec validate phase-0-cube-3d-model --strict` passes.

## 7. Phase 0 refinements (post-review)

- [x] 7.1 Edge beams: model the square truss section and light **2 rows per visible face** (chords); base edges light only the outward vertical face.
- [x] 7.2 Corner pieces: light the 12 edges of each corner cube (glowing outline) in addition to the X panels.
- [x] 7.3 Scenery: optional floor grid + rough speaker cabinets (sub + 2 mains), toggleable via `--no-floor`/`--no-speakers`, rendered depth-correctly.
- [x] 7.4 Navigation: add a fly/FPS camera (WASD + mouse-look) alongside orbit; `Tab` toggles and preserves the viewpoint.
- [x] 7.5 On-screen help overlay (Pillow text -> texture) showing the active mode + controls; `H` toggles.
- [x] 7.6 Update README (viewing + both navigation modes) and unit tests for the new topology.
- [x] 7.7 Scenery polish: clay ground + surrounding bushes (bush doof), blue marker LEDs at speaker bases, mains aligned into the sub's plane, and more ambient light (`--no-bushes` added).
