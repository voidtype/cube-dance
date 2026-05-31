## ADDED Requirements

### Requirement: Preset-driven element engine is the default visual

The default cube-aware visual SHALL be the **preset-driven element engine** (Phase 4), with
the audio **features extended** to include classified events, the sustained bass level, and
a beat phase. The `vu` meter and the no-audio placeholder SHALL remain available. The engine
SHALL still only write the shared `(N,3)` color buffer.

#### Scenario: Element engine drives the cube by default

- **WHEN** audio is loaded with the default (auto/spectrum) visual
- **THEN** the current preset's element engine drives the cube (corners on bass, beams on
  spectrum, plus event-triggered elements)

#### Scenario: VU still selectable

- **WHEN** the `vu` visual is selected
- **THEN** the Phase-1 VU meter drives the cube instead
