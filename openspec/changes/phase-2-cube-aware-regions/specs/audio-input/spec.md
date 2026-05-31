## ADDED Requirements

### Requirement: Frequency-band and stereo analysis

The source SHALL provide **frequency-band** energies — **bass**, **mid**, and **treble** —
as normalised values in `[0, 1]`, computed **per stereo channel** (left and right) and as
mono, queryable at any playback position alongside the overall level. Bands SHALL be
derived from the audio's spectrum (e.g. band-pass filtering) and normalised so each band's
loud passages approach `1.0`. A position outside `[0, duration]` SHALL clamp.

#### Scenario: Bands separate content by frequency

- **WHEN** the bands are queried during a bass-heavy passage versus a treble-heavy passage
- **THEN** the bass value is higher in the bass-heavy passage and the treble value is
  higher in the treble-heavy passage, each within `[0, 1]`

#### Scenario: Left/right split

- **WHEN** content is panned to one channel
- **THEN** that channel's band energy is greater than the other channel's for the same
  band

#### Scenario: Features at a position

- **WHEN** the current features are requested at playback position `t`
- **THEN** a feature set is returned carrying the overall level and the bass/mid/treble
  values (mono and per-channel) for `t` (clamped to the file)
