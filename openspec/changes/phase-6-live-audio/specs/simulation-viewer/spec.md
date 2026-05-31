## ADDED Requirements

### Requirement: Live input selection and device listing

The CLI SHALL provide a `--live` flag that drives the visuals from the live audio input, a
`--input-device` option to choose the device (name substring or index), an `--input-gain`
option to scale the captured level, and a `--list-audio-inputs` flag that prints the
available input devices and exits.

#### Scenario: Launch from live input

- **WHEN** the viewer is started with `--live`
- **THEN** the cube reacts to the live audio input rather than a file

#### Scenario: List input devices

- **WHEN** `--list-audio-inputs` is passed
- **THEN** the available input devices are printed and the program exits

### Requirement: The viewer indicates live mode

In live mode the HUD SHALL show a **LIVE** indicator and an elapsed time (no total duration or
transport position), since a live feed has no length or playhead.

#### Scenario: LIVE shown on the HUD

- **WHEN** running with a live input
- **THEN** the on-screen status shows a LIVE indicator instead of a `position / duration`
  transport line
