# simulation-viewer Specification

## Purpose
TBD - created by archiving change phase-0-cube-3d-model. Update Purpose after archive.
## Requirements
### Requirement: Interactive native window

The viewer SHALL open a native desktop window with an OpenGL context and render the cube
in real time. Closing the window SHALL shut the application down cleanly.

#### Scenario: Window opens and closes

- **WHEN** the application is launched in interactive mode on a desktop with a GPU
- **THEN** a native window opens showing the cube, and closing it exits the process with
  status 0

### Requirement: Render structure and LEDs from the color buffer

The viewer SHALL render the truss structure (the 12 edges and 8 corners) as a spatial
reference, and SHALL render every LED pixel as an emissive point whose color is read from
the model's color buffer. The rendered LED colors SHALL reflect the current buffer
contents, updated every frame.

#### Scenario: Buffer changes appear on screen

- **WHEN** a pixel's color in the buffer changes between frames
- **THEN** the corresponding rendered LED point shows the new color on the next rendered
  frame

#### Scenario: Structure is visible for orientation

- **WHEN** the cube is rendered
- **THEN** the 12 edges and 8 corner regions are visually identifiable as the cube's frame

### Requirement: Dual navigation modes

The viewer SHALL provide two navigation modes, switchable at runtime: an **orbit** mode
(3D-editor style: drag to orbit, scroll to zoom, drag-with-modifier to pan, distance
clamped so the cube cannot be lost) and a **fly** mode (FPS style: mouse-look with the
cursor captured, WASD to move, dedicated keys to rise/descend, and a move-speed control).
Switching modes SHALL preserve the current viewpoint so the user is not disoriented.

#### Scenario: Switch between orbit and fly

- **WHEN** the user toggles the navigation mode
- **THEN** the active mode changes between orbit and fly, the viewpoint is preserved
  across the switch, and the new mode's inputs take effect (orbit drag/scroll, or fly
  mouse-look + WASD)

#### Scenario: Orbit cannot lose the cube

- **WHEN** the user zooms in orbit mode
- **THEN** the camera distance changes and is clamped within configured min/max bounds

### Requirement: On-screen control help

The viewer SHALL display an on-screen help overlay showing the **active navigation mode**
and its controls, so it is always clear how to drive the scene. The overlay SHALL be
toggleable.

#### Scenario: Help reflects the active mode

- **WHEN** the help overlay is visible
- **THEN** it shows the current navigation mode and that mode's controls, and it can be
  hidden and shown again

### Requirement: Optional realism scenery

The viewer SHALL optionally render non-LED scenery to ground the cube in a stage-like
setting: a **clay ground**, surrounding **bushes**, and **speaker cabinets** (a sub and
two mains in a common plane) with small **blue marker LEDs** at their base. Each scenery
group (ground, speakers, bushes) SHALL be independently toggleable. Scenery SHALL be lit
with ambient + diffuse shading and rendered depth-correctly so it does not corrupt the
LED glow (solid scenery may occlude LEDs behind it while the LEDs themselves remain
additive).

#### Scenario: Scenery can be toggled

- **WHEN** the ground, speakers, or bushes are disabled in configuration
- **THEN** that scenery group is not rendered and the LEDs still render correctly

### Requirement: Real-time performance target

The viewer SHALL sustain at least **60 FPS** at the default dense pixel count on a typical
desktop GPU. Per-frame color updates SHALL be vectorised (no per-pixel Python loop in the
render hot path), and all LED pixels SHALL be drawn with a batched/instanced draw rather
than one draw call per pixel.

#### Scenario: Batched LED rendering

- **WHEN** the scene is rendered
- **THEN** all LED pixels are uploaded as a single buffer and drawn in a single
  batched/instanced draw call, and the per-frame color update touches the buffer as one
  vectorised operation

### Requirement: Placeholder non-audio test pattern

In the absence of audio input, the viewer SHALL animate the color buffer over time with a
documented placeholder pattern (an edge sweep plus a corner pulse) so density, addressing,
and the buffer→render pipeline can be validated visually. This pattern is explicitly
temporary scaffolding that later phases replace.

#### Scenario: Pattern animates and distinguishes regions

- **WHEN** the application runs with no audio source
- **THEN** the LED colors change over time, and the edge pixels and corner pixels are
  driven by visibly distinct behaviour (sweep vs pulse)

### Requirement: Headless self-test path

The system SHALL provide a headless self-test mode that builds the model, advances the
placeholder pattern for a number of frames, and reports stats (pixel count, buffer shape,
timing) **without opening a window or requiring a display**. This validates the data path
on machines or CI without a GPU session.

#### Scenario: Self-test runs without a display

- **WHEN** the application is run in self-test mode
- **THEN** it builds the model, advances the pattern for the requested frames, prints the
  pixel count and buffer shape, and exits with status 0 without opening a window

