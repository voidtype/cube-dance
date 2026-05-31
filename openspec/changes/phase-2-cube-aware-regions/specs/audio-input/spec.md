## ADDED Requirements

### Requirement: Streaming spectral analysis (per channel)

The system SHALL analyse audio **in real time at the current playback position** — from a
short recent window, **not** by precomputing the whole file — into **per-channel**
(left/right) **frequency buckets** (log-spaced). The same windowed interface SHALL be usable
for a file slice now and a live input stream later, and loading a file SHALL NOT do any
spectral precompute (no load-time stall).

#### Scenario: Buckets separate frequency content

- **WHEN** a window of mostly low-frequency content is analysed versus mostly
  high-frequency content
- **THEN** the low buckets are louder for the former and the high buckets for the latter

#### Scenario: Per-channel split

- **WHEN** content is present in only one channel
- **THEN** that channel's bucket energy exceeds the other channel's

#### Scenario: No whole-file precompute

- **WHEN** an audio file is loaded
- **THEN** no full-file spectral analysis is performed at load time; analysis happens per
  frame at the playhead

### Requirement: Adaptive dynamic levelling

The system SHALL adaptively level the analysed features so the visualisation is musically
useful on any track: each bucket SHALL be **auto-levelled** to its own recent range (so a
track shows all its bands — a "nice mix"), and an overall **presence** derived from recent
loudness SHALL gate the output so that **quiet passages are attenuated exponentially**
relative to the recent track level while loud passages reach full range. The references
SHALL adapt over time (so a uniformly quiet track still fills the range). The levelling
SHALL be streaming (stateful, no precompute) and its parameters SHALL be configurable.

#### Scenario: Quiet section hides, loud section shows

- **WHEN** a loud passage is followed by a much quieter passage in the same stream
- **THEN** the quiet passage's output is markedly lower than the loud passage's (hidden
  more than linearly)

#### Scenario: Quiet track still levels up

- **WHEN** a stream is quiet throughout
- **THEN** its features still adapt to fill a useful range over time
