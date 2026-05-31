## ADDED Requirements

### Requirement: Feature set carries per-channel frequency buckets

The visual feature set SHALL carry, in addition to the overall level, the **per-channel
frequency buckets** (left and right) and convenience aggregates (bass/mid/treble, and
left/right bass), so a visual can react to frequency content and stereo position. Existing
visuals that use only the level SHALL continue to work unchanged.

#### Scenario: Buckets available to visuals

- **WHEN** a visual is updated with the current features while audio plays
- **THEN** the features expose the left and right bucket arrays plus level and the
  band aggregates

### Requirement: Cube-aware, stereo, evolving visual

The system SHALL provide a cube-aware visual mapping frequency and stereo to cube regions:
- **Corners ← bass**, split **left/right** by channel (left-hand corners follow the left
  channel's bass, right-hand corners the right).
- **Beams ← the spectrum**: frequency SHALL run **along** each beam (low→high) so a beam is
  a small spectrum rather than one flat colour, and beams SHALL **lateralise by stereo**
  (left-side beams follow the left channel, right-side the right, centre beams the mono mix)
  — content panned to one side shows on that side.
- Brightness SHALL come from the dynamically-levelled features (stark: quiet hides).
- Colours SHALL **evolve over time and accelerate** (a hue drift whose rate grows over a
  set), mapped per frequency.
All parameters SHALL be held in a configurable params object (for the later DSL), and the
visual SHALL write only the shared `(N,3)` color buffer.

#### Scenario: Bass corners, spectrum beams

- **WHEN** a bass-heavy moment occurs
- **THEN** the corners brighten more than the beams
- **WHEN** higher-frequency content occurs
- **THEN** the beams brighten, with hue varying along the beam by frequency

#### Scenario: Stereo lateralises

- **WHEN** content is panned to one channel
- **THEN** that side's corners/beams respond more strongly than the other side's

#### Scenario: Colour evolves over time

- **WHEN** the visual runs for a while
- **THEN** the hues drift (and the drift accelerates), so the look is not static

### Requirement: Visual selection

The application SHALL let the active visual be selected (cube-aware **spectrum**, the
Phase-1 **vu** meter, or **auto**). **auto** SHALL use the cube-aware visual when an audio
source is present and the placeholder pattern otherwise.

#### Scenario: Selecting a visual

- **WHEN** the user selects the `vu` visual with audio loaded
- **THEN** the VU meter drives the cube
- **WHEN** the user selects `auto` (the default) with audio loaded
- **THEN** the cube-aware spectrum visual drives the cube
