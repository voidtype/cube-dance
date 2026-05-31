# visual-engine Specification

## Purpose
TBD - created by archiving change phase-4-visual-dsl. Update Purpose after archive.
## Requirements
### Requirement: Composable element engine

The system SHALL provide a visual engine that runs an ordered set of **elements**, each
writing into the `(N,3)` color buffer over a target **region** with a **blend mode** (add /
max / over); the composited result is the frame. Each element receives a shared **context**
(the frame's events, continuous features, beat phase, time, and the cube model). The engine
SHALL write only the existing color buffer.

#### Scenario: Elements composite

- **WHEN** the engine runs two elements targeting different regions
- **THEN** both contributions appear in the output buffer

### Requirement: Event subscription and modulators

Elements SHALL be able to **subscribe** to event classes — a fired event of a subscribed
class triggers the element's response (e.g. a decaying flash/sparkle) — and to continuous
features. Element parameters MAY be driven by **modulators**: LFOs, feature-envelope
followers, and time **evolvers** whose rate can **accelerate** over time.

#### Scenario: A subscribed event triggers the element

- **WHEN** a `kick` event occurs and an element subscribes to `kick`
- **THEN** that element produces its response that frame and decays afterwards
- **WHEN** no events occur
- **THEN** the element idles (no spurious response)

### Requirement: Evolution and composition awareness

The engine SHALL **evolve over time driven by the music**: an energy accumulator advances a
global state and **accelerating** evolvers shift palette/intensity so a long set does not
look static. It SHALL track a lightweight **composition/energy state** (energy + onset
density) so the look can respond to build-ups and drops.

#### Scenario: Energy advances the evolution

- **WHEN** sustained high-energy audio plays for a while
- **THEN** the evolution state advances (palette/intensity changes) compared with silence

