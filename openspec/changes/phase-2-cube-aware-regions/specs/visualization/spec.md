## ADDED Requirements

### Requirement: Feature set carries frequency bands

The visual feature set SHALL carry, in addition to the overall level, the **bass**, **mid**,
and **treble** band energies (mono) and the per-channel **bass_l** and **bass_r**, so a
visual can react to frequency content and stereo position. Existing visuals that use only
the level SHALL continue to work unchanged.

#### Scenario: Bands available to visuals

- **WHEN** a visual is updated with the current features while audio plays
- **THEN** the features expose level plus bass/mid/treble and left/right bass values

### Requirement: Cube-aware spectrum visual

The system SHALL provide a **cube-aware** visual that maps frequency bands to cube regions:
the **corners** SHALL respond to **bass**, split **left/right** by channel (left corners
driven by left-channel bass, right corners by right-channel bass), and the **beams**
(edges) SHALL respond to **mid/treble**. Band responses SHALL be smoothed (fast attack,
slower release) and the visual MAY evolve gently over time (e.g. slow hue drift). It writes
only the shared `(N,3)` color buffer.

#### Scenario: Bass lights the corners, treble lights the beams

- **WHEN** a bass-heavy moment occurs
- **THEN** the corner pixels brighten more than the edge pixels
- **WHEN** a treble-heavy moment occurs
- **THEN** the edge (beam) pixels brighten relative to the corners

#### Scenario: Stereo splits left/right corners

- **WHEN** bass is stronger in the left channel than the right
- **THEN** the left-hand corners are brighter than the right-hand corners

### Requirement: Visual selection

The application SHALL let the active visual be selected (cube-aware **spectrum**, the
Phase-1 **vu** meter, or **auto**). **auto** SHALL use the cube-aware visual when an audio
source is present and the placeholder pattern otherwise.

#### Scenario: Selecting a visual

- **WHEN** the user selects the `vu` visual with audio loaded
- **THEN** the VU meter drives the cube
- **WHEN** the user selects `auto` (the default) with audio loaded
- **THEN** the cube-aware spectrum visual drives the cube
