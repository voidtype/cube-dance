# recording Specification

## Purpose
TBD - created by archiving change session-recording. Update Purpose after archive.
## Requirements
### Requirement: Toggle live recording in-session

The viewer SHALL let the user start and stop recording during a session via a key, and
MAY auto-start at launch via a flag and stop on quit. While recording, the viewer SHALL
show an on-screen recording indicator with elapsed time, and the captured file SHALL
exclude the on-screen help/indicator overlay (the clip shows only the visualisation).

#### Scenario: Toggle produces a file

- **WHEN** the user toggles recording on and then off after some time
- **THEN** a video file is written for that interval and the on-screen indicator shows
  while active and clears when stopped

#### Scenario: Overlay excluded from the clip

- **WHEN** a recording is captured while the help overlay is visible
- **THEN** the recorded frames contain the visualisation only, not the overlay

### Requirement: Shareable MP4 output

The recorder SHALL write an **MP4** with **H.264 video** in `yuv420p` and, when audio is
present, **AAC audio**, using `+faststart` and even pixel dimensions, so the file plays on
common platforms (e.g. Facebook) without re-encoding.

#### Scenario: Container and codecs

- **WHEN** a recording with audio finishes
- **THEN** the output is an `.mp4` containing exactly one H.264 video stream and one AAC
  audio stream

### Requirement: Fixed-rate capture of the rendered visualization

The recorder SHALL capture the application's own rendered frames at a configurable target
framerate that is independent of the live render rate, so the recorded video plays at the
correct speed.

#### Scenario: Duration matches real time

- **WHEN** a recording runs for `T` seconds of wall-clock time at target framerate `F`
- **THEN** the output video duration is approximately `T` seconds (within a small
  tolerance) and reports framerate `F`

### Requirement: Mux the audio that played

The recorder SHALL include the segment of the source audio corresponding to the recording
window, aligned with the video. A looped source SHALL wrap; a non-looped source SHALL
zero-pad past its end. When the source is muted the audio SHALL still be muxed; when there
is no audio source the output SHALL be video-only.

#### Scenario: Audio segment matches the recording window

- **WHEN** recording starts at audio position `p` and runs for `T` seconds
- **THEN** the muxed audio is the source audio from `p` for `T` seconds (wrapped if the
  source loops)

#### Scenario: No audio source

- **WHEN** recording with no audio source (placeholder visuals)
- **THEN** a valid video-only MP4 is produced

### Requirement: Robust ffmpeg handling and finalisation

The recorder SHALL locate an ffmpeg binary from the environment, the `PATH`, or a bundled
fallback, and SHALL finalise the output file if the window is closed while recording. If
encoding cannot start it SHALL report a clear error rather than crashing the viewer.

#### Scenario: Closing mid-recording still yields a file

- **WHEN** the window is closed while a recording is in progress
- **THEN** the in-progress recording is finalised into a playable file

#### Scenario: ffmpeg missing

- **WHEN** no ffmpeg binary can be found
- **THEN** starting a recording reports a clear error and the viewer keeps running

