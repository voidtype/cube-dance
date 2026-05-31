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

### Requirement: Multi-deck preset mixer is the default visual

The default `spectrum` visual SHALL be a **deck mixer** running **four independent preset
decks** at once, blended into the shared `(N,3)` buffer. Each deck SHALL have its own preset
and its own evolution state, and SHALL be weighted by a per-deck **volume**; the blend SHALL
be additive and clipped to `[0,1]`.

#### Scenario: Decks blend by volume

- **WHEN** two decks have volume `1.0` and `0.0`
- **THEN** only the deck at `1.0` contributes to the cube

#### Scenario: Decks evolve independently

- **WHEN** two decks run different presets and are both audible
- **THEN** each advances its own colour evolution (the layers are visually distinct)

### Requirement: Engine exposes a buffer-targeted render alongside update

The visual engine SHALL provide a render entry point that composites its elements into a
**caller-supplied buffer** without applying master brightness or clipping, so the mixer can
weight and accumulate decks. The existing `update(model, t, features)` SHALL remain for the
standalone path and SHALL still apply master and clip.

#### Scenario: Mixer composites via render

- **WHEN** the mixer renders a deck
- **THEN** the engine writes that deck's contribution into the provided buffer and the mixer
  applies the deck volume, then master and clip once for the final image

### Requirement: Each deck has knob params and pad triggers

Each deck SHALL hold **knob params** (intensity, hue, evolution speed, spatial size) that
shape its output live, and a set of **triggers** that, when fired, spawn **transient
elements** composited until they self-expire. Triggers and knob defaults/labels SHALL come
from the deck's preset.

#### Scenario: Firing a trigger spawns a transient effect

- **WHEN** a deck trigger is fired
- **THEN** a transient element is added to that deck, drawn for its lifetime, then removed

#### Scenario: Knob params shape one deck

- **WHEN** a deck's intensity param is lowered
- **THEN** that deck's output dims while the other decks are unaffected

### Requirement: Global flags shape every deck

The engine/mixer SHALL honor global flags: **mono** (stark/desaturated), **freeze** (hold
the palette), **reverse** (flip colour drift), **size boost**, **sync pulse** (brighten on
detected kicks), and **blackout** (kill output).

#### Scenario: Freeze holds the palette

- **WHEN** freeze is enabled
- **THEN** the global hue evolution stops advancing until freeze is released

#### Scenario: Mono renders stark

- **WHEN** mono is enabled
- **THEN** elements render with zero saturation (white/greyscale) instead of their hues

