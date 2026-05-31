## ADDED Requirements

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
