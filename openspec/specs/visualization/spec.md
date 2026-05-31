# visualization Specification

## Purpose
TBD - created by archiving change phase-1-audio-vu-meter. Update Purpose after archive.
## Requirements
### Requirement: Audio-driven color buffer

The visualisation layer SHALL write the model's `(N, 3)` color buffer each frame from the
current audio features. When an audio source is present it SHALL drive the buffer from the
audio; when no audio source is present it SHALL fall back to the Phase 0 placeholder
pattern. The layer SHALL only write the existing color buffer (it SHALL NOT change the
buffer shape or pixel addressing).

#### Scenario: Audio level changes the output

- **WHEN** the active visual is updated with a high audio level and then with a low audio
  level
- **THEN** the high-level frame has more lit (or brighter) pixels than the low-level frame

#### Scenario: No audio falls back to the placeholder

- **WHEN** the application runs with no audio source
- **THEN** the placeholder pattern drives the color buffer (the Phase 0 behaviour)

### Requirement: VU meter visual

The system SHALL provide a **VU meter** visual that maps the current loudness level to a
**vertical fill** of the cube: pixels below the current level (by normalised height from
floor to top) are lit and pixels above are off (or dim). The fill SHALL be coloured on a
**green → amber → red** ramp by height, with **level-driven brightness**, and SHALL show a
brief **peak-hold** cap at the highest recent level. The displayed level SHALL be smoothed
with **fast attack and slower release** so it reads like a real meter.

#### Scenario: Fill height tracks level

- **WHEN** the VU meter is driven at level `0.0`, `0.5`, and `1.0` (after settling)
- **THEN** the lit fraction of the cube (by height) is approximately none, about half, and
  approximately full, respectively

#### Scenario: Colour ramps by height

- **WHEN** the meter is filled
- **THEN** lit pixels near the floor are green-biased and lit pixels near the top are
  red-biased

#### Scenario: Release decays gradually

- **WHEN** the input level drops sharply from high to `0.0`
- **THEN** the displayed fill decreases gradually over subsequent frames (release), rather
  than dropping to zero in a single frame

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

