## ADDED Requirements

### Requirement: Load and decode an audio file

The system SHALL load an audio file into floating-point samples, exposing its **sample
rate**, **duration**, channel layout, and a **mono mix**. Supported formats SHALL include
the common uncompressed/lossless types decodable by the audio backend (WAV, FLAC, AIFF,
OGG). An unreadable or missing file SHALL raise a clear error rather than failing silently.

#### Scenario: Known file decodes with correct metadata

- **WHEN** a WAV file of known duration `D` and sample rate `R` is loaded
- **THEN** the source reports sample rate `R` and duration `D` within one sample frame,
  and exposes a mono sample array

#### Scenario: Missing file errors clearly

- **WHEN** a path that does not exist is loaded
- **THEN** loading raises a clear, descriptive error

### Requirement: Loudness envelope and level at position

The source SHALL compute a **loudness envelope** (per-hop RMS) over the file and SHALL
return a **normalised level in `[0, 1]`** for any playback position. Positions outside
`[0, duration]` SHALL clamp. The envelope SHALL be normalised so that the loudest part of
the file approaches `1.0`.

#### Scenario: Louder sections read higher than quieter ones

- **WHEN** the level is queried at a position in a loud section and at a position in a
  quiet section of the same file
- **THEN** the loud-section level is greater than the quiet-section level, and both are
  within `[0, 1]`

#### Scenario: Position clamps to the file

- **WHEN** the level is queried at a negative position or beyond the duration
- **THEN** the position is clamped into `[0, duration]` and a valid level in `[0, 1]` is
  returned

### Requirement: Playback transport

The source SHALL provide a **transport** that tracks the current playback **position in
seconds** and supports **play**, **pause**, **restart**, and **seek**. Position SHALL
advance only while playing and SHALL remain within `[0, duration]`. The transport SHALL
report whether it is playing and whether playback has reached the end.

#### Scenario: Position advances only while playing

- **WHEN** the transport is playing and time `dt` elapses
- **THEN** the position increases by `dt` (clamped at the duration)
- **WHEN** the transport is paused and time `dt` elapses
- **THEN** the position does not change

#### Scenario: Seek and restart

- **WHEN** the transport is told to seek to time `t` within `[0, duration]`
- **THEN** the reported position becomes `t`
- **WHEN** the transport is restarted
- **THEN** the position returns to `0`

### Requirement: Synced playback with graceful fallback

The source SHALL play the audio to the default output device and keep the **visual
position synced to the audio stream**. When no output device or stream is available, or
when muted, the source SHALL fall back to a **silent virtual transport** (advanced by the
caller's frame time) so the visualisation still runs without raising.

#### Scenario: Runs without an audio device

- **WHEN** no audio output device is available (or the source is muted)
- **THEN** starting the source does not raise, the transport still advances while playing,
  and levels are still returned for the current position
