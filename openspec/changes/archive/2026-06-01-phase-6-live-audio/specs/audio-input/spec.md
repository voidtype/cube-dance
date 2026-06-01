## ADDED Requirements

### Requirement: Live audio input source

The system SHALL provide a **live audio input** source that captures from a `sounddevice`
input (line/mic) into a rolling ring buffer and exposes the same windowed contract as the
file source (`sr`, `channels`, `window_at(t, win)`, `level_at`). `window_at` SHALL return the
**most recent** `win` samples (live is always "now"). The source SHALL present **stereo**
(mono inputs duplicated) and SHALL apply an **input gain**. The device SHALL open on a
background thread and degrade to silence if unavailable.

#### Scenario: The window follows the live input

- **WHEN** new audio arrives on the input stream and `window_at` is called
- **THEN** it returns the latest `win` samples of captured audio

#### Scenario: Mono input is presented as stereo

- **WHEN** the input device is mono
- **THEN** the window is duplicated to two channels so the L/R features still work

#### Scenario: No device degrades cleanly

- **WHEN** no input device is available or it fails to open
- **THEN** the source stays silent and the viewer keeps running (no crash)

### Requirement: Live transport semantics

When the audio source is live, there SHALL be **no output playback** and **no seek/transport**
(a live feed cannot be repositioned). The position SHALL be a wall-clock elapsed time used
only for display, the source SHALL never report "finished", and `features(dt)` SHALL analyse
the latest window exactly as for a file.

#### Scenario: Live source never finishes

- **WHEN** the live source runs for any length of time
- **THEN** it never reports finished and keeps producing features from the latest audio

#### Scenario: Seek is inert when live

- **WHEN** a seek/restart is requested on a live source
- **THEN** it has no effect (the live feed cannot be repositioned)
