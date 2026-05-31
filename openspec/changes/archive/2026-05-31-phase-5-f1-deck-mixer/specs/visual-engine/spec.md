## ADDED Requirements

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
