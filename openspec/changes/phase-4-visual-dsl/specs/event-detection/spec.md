## ADDED Requirements

### Requirement: Classified transient events (streaming)

The system SHALL detect onsets from per-band spectral flux on each analysis window (real
time, no precompute) and **classify** each onset into a class — at least `kick`, `hat`,
`snare`, `perc` — using heuristic features (dominant band, spectral centroid,
flatness/noisiness, energy). It SHALL emit discrete **events** carrying the class and a
strength in the frame in which they occur, with a per-class refractory period to avoid
double-triggering.

#### Scenario: Low sharp hit vs high noisy hit

- **WHEN** a low-frequency sharp transient occurs
- **THEN** a `kick` event is emitted
- **WHEN** a high-frequency noisy transient occurs
- **THEN** a `hat` event is emitted

#### Scenario: Events are real-time

- **WHEN** the detector is run window-by-window over a stream
- **THEN** events are produced as transients occur, with no whole-file precompute

### Requirement: Sustained bass stream and kick/bass disambiguation

The system SHALL provide a **continuous bass level** from a sub-band (~30–120 Hz) envelope
follower, separate from the transient events, plus its rate of change. **Kick versus bass**
SHALL be resolved by attack sharpness/duration: a short, sharp sub-band transient is a
`kick` event, whereas sustained sub-band energy is reported as the bass **level** (not a
stream of kick events).

#### Scenario: Sustained bass is a level, not kicks

- **WHEN** a sustained low tone plays
- **THEN** the bass level is high and no continuous stream of kick events is emitted

#### Scenario: A kick is an event

- **WHEN** a short, sharp low-frequency hit occurs
- **THEN** a `kick` event is emitted at that moment
