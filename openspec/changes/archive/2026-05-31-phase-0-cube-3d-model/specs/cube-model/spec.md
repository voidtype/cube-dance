## ADDED Requirements

### Requirement: Geometry derived from the truss reference

The system SHALL construct the cube geometry from the constants in
`reference/whole_cube.scad`: a cube **2.60 m** per side, with **2.00 m** lit edge runs
and **0.30 m** corner cubes at the 8 vertices. The geometry SHALL be expressed in
**meters**, **centered at the origin** (spanning `[-1.30, +1.30] m` on each axis), with
**+Y up**. The model SHALL expose the 12 edges and 8 corners as identifiable structural
elements.

#### Scenario: Cube extents match the reference

- **WHEN** the geometry is built with default parameters
- **THEN** its axis-aligned bounding box spans `[-1.30, +1.30] m` (±1 mm) on X, Y, and Z

#### Scenario: Edge and corner counts

- **WHEN** the geometry is built
- **THEN** it reports exactly 12 edges and 8 corners

### Requirement: Dense multi-row LED topology on edge beams

Each of the 12 edges SHALL be modelled as a square-section truss beam whose LEDs run
along its chords. The model SHALL place a dense, evenly spaced run of abstract LED pixels
along each lit chord over the central **2.0 m** of the beam, at a configurable linear
density (LEDs/m) with a **dense default**. **Two rows SHALL be lit per visible outward face**: top and vertical
edges therefore light the chords of both outward faces (the shared corner chord giving
three rows total), while **base edges** (the bottom square, resting on the floor) SHALL
light only their outward vertical face — omitting the ground-facing and up-facing rows
that would be invisible or stepped on. Pixels are abstract, not models of individual
physical LEDs.

#### Scenario: Rows per edge

- **WHEN** the topology is built
- **THEN** each base (floor) edge lights 2 chord rows and every other edge lights 3, and
  all base-edge rows sit on that edge's outward vertical face

#### Scenario: Edge pixel count follows configured density

- **WHEN** the topology is built with edge density `D` LEDs/m
- **THEN** each lit chord row contains `round(D × 2.0)` pixels and the total edge-pixel
  count is `(sum of lit rows over all 12 edges) × round(D × 2.0)`

#### Scenario: Edge pixels lie on their chord rows

- **WHEN** the topology is built
- **THEN** every edge pixel lies within 1 mm of one of its edge's chord rows and within
  `[-1.0, +1.0] m` along the edge axis

### Requirement: Corner pieces are fully lit and denser

Each of the 8 corners SHALL be modelled as a **0.30 m corner cube**: the model SHALL
light the **12 edges of the corner cube** (its glowing outline) and SHALL add **X-shaped**
LED runs (crossed diagonals) on its outward faces, all within the outer 0.30 m corner
region. Corner LED
linear density SHALL be **greater than** the edge density, so corners read as a distinct,
denser visual feature.

#### Scenario: Corners are denser than edges

- **WHEN** the topology is built
- **THEN** the corner LED linear density is strictly greater than the edge LED linear
  density

#### Scenario: Each corner is lit on its cube edges and X panels

- **WHEN** the topology is built
- **THEN** every one of the 8 corners contributes LED pixels along the 12 edges of its
  corner cube plus at least one pair of crossed diagonal runs, all within its 0.30 m
  corner region

### Requirement: Stable per-pixel addressing

Every LED pixel SHALL have a stable integer address. For a given configuration the
addresses SHALL be the contiguous range `0 .. N-1` and SHALL map to the same physical
position and the same structural element on every build. The model SHALL expose pixel
positions as an `(N, 3)` float array (meters) aligned to the address index.

#### Scenario: Deterministic addressing

- **WHEN** the topology is built twice with identical configuration
- **THEN** both builds produce the same pixel count `N`, identical positions per index,
  and identical structural assignments per index

#### Scenario: Contiguous index space

- **WHEN** the topology is built
- **THEN** pixel addresses are exactly the integers `0` through `N-1` with none missing
  or duplicated

### Requirement: Structural regions

The model SHALL expose, for every pixel address, the structural element it belongs to:
its **edge id** (`0..11`) or **corner id** (`0..7`), and a **structural group** of either
`edge` or `corner`. The regions SHALL partition the pixels — every pixel belongs to
exactly one structural element, and the union of all regions is all pixels.

#### Scenario: Every pixel has exactly one structural element

- **WHEN** any pixel address `i` in `0..N-1` is queried
- **THEN** it returns exactly one structural group (`edge` or `corner`) and exactly one
  element id valid for that group

#### Scenario: Regions partition the pixel set

- **WHEN** the union of all edge regions and all corner regions is taken
- **THEN** it equals the full set of pixel addresses `0..N-1` with no overlap

### Requirement: LED color buffer contract

The model SHALL expose a single mutable color buffer shaped `(N, 3)` of floats in the
range `[0.0, 1.0]` (linear RGB), aligned to the pixel address index, initialised to
zeros (all LEDs off). This buffer SHALL be the single shared write surface that visual
generators populate and the viewer renders; later phases write to it without changing
its shape or indexing.

#### Scenario: Buffer shape and initial state

- **WHEN** the model is created
- **THEN** the color buffer has shape `(N, 3)`, dtype float, and all values are `0.0`

#### Scenario: Writes are addressable and read back

- **WHEN** a color is written at pixel address `i`
- **THEN** reading address `i` of the buffer returns that color and no other address is
  modified
