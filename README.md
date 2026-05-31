# Cube Dance

Sound-reactive LED control software and 3D simulation for a **2.6 m F34 truss cube**
used at dance-music events. The lights are primarily sound-reactive and evolve over time;
downstream mapping software (MadMapper) drives the physical pixels.

This repo is built **spec-first** with [OpenSpec](https://github.com/Fission-AI/OpenSpec)
and developed in **phases** — see [`openspec/project.md`](openspec/project.md) for the
full roadmap and the physical cube facts.

## Status: Phase 4 — evolving visual engine (event-driven, preset-authored)

The default `spectrum` visual is now a **layered element engine** fed by **classified
musical events**, not just raw bands:

- **Event detection** (streaming, heuristic): per-band spectral-flux onsets → classify
  **kick / hat / snare / perc**; sustained bass stays the continuous stream (kick-vs-bass by
  attack). Rough tempo/beat phase.
- **Elements** subscribe to events + features and composite: `BassCorners`, `SpectrumBeams`,
  `KickPulse`, `HatSparkle`, `Sweep`, `Chase`, `AmbientWash`, with LFO/envelope/evolver
  modulators.
- **Evolution + composition awareness**: energy/onset-density tracking + an **accelerating**
  hue drift so a set keeps changing.
- **Python presets** author the look: `presets/<name>.py` with `build(engine)`. Pick with
  `--preset deep|punchy`; press **`N`** to cycle live.

```bash
uv run cube-dance --audio track.wav --preset punchy   # then N to cycle presets
```

## Status: Phase 3 — F1 control

Press **`C`** for an on-screen **Traktor Kontrol F1** in the right quarter (mouse is freed
and camera movement freezes while it's up). Its **knobs and faders are click-drag** (VST
style), **buttons are grey and light when clicked**, a **7-segment display** shows P and the
**browse encoder** (scroll over it) changes P. Controls map to the visual/AGC params: knobs
→ hide-quiet / contrast / hue-spread / response; faders → master / evolve / accel / floor;
P → global hue; REVERSE flips the colour-drift direction. A connected real F1 feeds the same
controls over MIDI (best-effort; full mapping in Phase 5).

## Status: Phase 2 — cube-aware, dynamic & stereo

Load an audio file (or the built-in demo beat) and the cube reacts **spatially and
musically**:

- **Corners ← bass**, split **left/right** by stereo channel.
- **Beams ← the spectrum**: frequency runs *along* each beam (low→high), and beams
  **lateralise by stereo** — content panned left lights the left beams, right the right.
- **Dynamic auto-levelling**: each band adapts to the track (so any mix looks good) while
  **quiet passages exponentially hide** and loud ones pop. Analysis is **streaming** (a
  short window at the playhead — no precompute, instant load, and ready for live input).
- **Colours evolve and accelerate** over a set, per frequency.

Audio plays out loud, synced to the visuals; the device opens in the background so the
window appears instantly. With no audio it falls back to the Phase 0 placeholder.

```bash
uv run cube-dance --demo                       # synthetic beat, no file needed
uv run cube-dance --audio track.wav            # your own file (WAV/FLAC/AIFF/OGG)
uv run cube-dance --audio track.wav --visual vu    # the simple Phase-1 VU meter instead
uv run cube-dance --audio track.wav --mute     # visuals only, no sound
```

`--visual`: `auto` (default — cube-aware "spectrum" with audio), `spectrum`, or `vu`.
Transport: **`K`** play/pause · **`J`** restart (shown in the on-screen help).

### Record a clip to share

Press **`V`** to start/stop recording (or pass `--record` to start at launch and stop on
quit). It captures the live window — your camera moves and all — to a **Facebook-ready
MP4** (H.264 + AAC, `+faststart`) and muxes the audio that played. The on-screen help/REC
overlay is **not** in the clip. Files land in `recordings/cube-<timestamp>.mp4`.

```bash
uv run cube-dance --demo --record           # auto-record from launch
uv run cube-dance --audio track.wav         # then press V to start/stop
uv run cube-dance --demo --record-fps 60 --record-dir ~/Desktop
```

The audio is muxed even with `--mute` (so the clip has sound); with no audio source the
clip is video-only. Needs `ffmpeg` (uses your system one, or the bundled `imageio-ffmpeg`).

### The cube (Phase 0 foundation)

An explorable native 3D simulation of the cube with a dense, abstract LED representation:

- **12 edge beams**, each lit with **2 rows per visible face** (the truss chords) — so
  top/vertical edges show ~3 parallel rows; the **base edges** light only their outward
  vertical face (ground-/up-facing rows are skipped, as they'd be invisible or stepped on).
- **8 corner cubes** lit on their **edges** (the glowing ⊠ outline) plus **X-panels** —
  denser, and a deliberate visual feature.
- A **dull-aluminium F34 truss** beneath the LEDs — the 4 chords per beam (the LED rows
  sit on them), diagonal lacing (the triangles) on the visible faces, and corner-cube
  frames. Shaded as metal that reacts to light. Toggle with `--no-truss`.
- Optional **scenery** for realism: a **clay ground**, surrounding **bushes** (it's a
  bush doof), and rough **speaker** cabinets (one sub front-centre, two mains in the same
  plane) with little **blue marker LEDs** at their base. Toggle with `--no-floor` /
  `--no-speakers` / `--no-bushes`.
- A single `(N, 3)` RGB **color buffer** is the hand-off contract every later phase writes.
- A placeholder, non-audio test pattern (edge sweep + corner pulse) animates the buffer
  so you can see the pixels light up. (Phase 1 replaces it with audio.)

~9,700 LED pixels at default density; renders as a glowing truss cube on a stage.

## Requirements

- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/).
- A desktop GPU. On macOS it uses OpenGL 4.1 (via Metal) through the **glfw** backend.

## Run

```bash
uv run cube-dance              # launch the interactive viewer
uv run cube-dance --selftest   # headless data-path check (no window)
```

Options:

```bash
uv run cube-dance --edge-density 144 --corner-density 200   # denser LEDs
uv run cube-dance --no-floor --no-speakers --no-bushes      # hide scenery
```

### Navigating the scene

There are **two navigation modes** — press **`Tab`** to switch. The active mode and its
controls are always shown in the on-screen help (toggle with **`H`**).

**Fly mode** (like an FPS) — **default** (the mouse is captured for look; press `Tab` for
orbit):

| Input            | Action            |
| ---------------- | ----------------- |
| Mouse            | look              |
| `W` `A` `S` `D`  | move              |
| `Space` / `E`    | up                |
| `Ctrl` / `Q`     | down              |
| `Shift` (hold)   | move faster       |
| Scroll           | adjust move speed |

**Orbit mode** (like a 3D editor / Blender) — press `Tab` to enter:

| Input                           | Action |
| ------------------------------- | ------ |
| Left-drag                       | orbit around the cube |
| Shift-drag / right- or mid-drag | pan    |
| Scroll                          | zoom   |

**Always available:** `R` reset view · `V` record clip · `C` F1 controls · `N` cycle preset ·
`H` toggle help · `Esc` quit.
With audio: `K` play/pause · `J` restart. With no audio: `P` pause/resume the placeholder
pattern.

moderngl-window flags pass through, e.g. `uv run cube-dance --window glfw --vsync True`.

## Develop

```bash
uv run pytest        # unit tests + offscreen GPU render test (skips if no GL)
```

### Layout

```
cube_dance/
  config.py         CubeConfig — dimensions (from the SCAD), densities, scenery toggles
  geometry.py       12 edges (beam chords) + 8 corner cubes, deterministic ordering
  led_topology.py   dense LED pixels, addressing, regions -> CubeModel + color buffer
  patterns.py       placeholder test pattern (no-audio fallback)
  scenery.py        clay ground + bushes + speaker cabinets (non-LED realism props)
  truss.py          F34 truss tubes (chords + lacing + corner frames) for the metal pass
  led_mesh.py       emissive LED-strip tubes (one per run), coloured per-pixel from a texture
  audio/            decode + window_at, streaming analyzer + AGC, event detection, transport
  visuals/          VU + placeholder + params; engine/ (elements, modulators, evolution)
  presets/          Python presets: build(engine) composes elements (deep, punchy)
  control/          F1 control state, control->param mapping, basic MIDI input
  render/virtual_f1.py   interactive on-screen F1 panel (knobs/faders/buttons/display/pads)
  recording.py      live-session capture -> shareable MP4 (ffmpeg)
  render/camera.py  orbit + fly cameras (numpy matrices)
  render/scene.py   moderngl: LED points (single draw) + scenery, depth-correct
  render/hud.py     on-screen help overlay (Pillow text -> texture)
  app.py            moderngl-window viewer (render loop, dual nav modes, input, recording)
  selftest.py       headless data-path validation
  cli.py            entrypoint (cube-dance / python -m cube_dance)
reference/whole_cube.scad   the source-of-truth OpenSCAD model
openspec/                   specs, project context, and per-phase change proposals
```

### OpenSpec workflow

Each phase is one change under `openspec/changes/`. Capabilities live in
`openspec/specs/` and accrete as changes are archived. The OpenSpec CLI needs Node ≥ 18:

```bash
openspec list                          # active changes
openspec validate <change> --strict    # validate a change
openspec show <change>                 # view proposal/specs/tasks
```
