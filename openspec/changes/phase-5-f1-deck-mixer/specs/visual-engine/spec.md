## ADDED Requirements

### Requirement: Multi-deck preset mixer is the default visual

The default `spectrum` visual SHALL be a **deck mixer** running **four independent preset
decks** at once, blended into the shared `(N,3)` buffer. Each deck SHALL have its own preset
and its own evolution state, and SHALL be weighted by a per-deck **volume**; the blend SHALL
be additive and clipped to `[0,1]`. The decks SHALL share one global parameter set.

#### Scenario: Decks blend by volume

- **WHEN** two decks have volume `1.0` and `0.0`
- **THEN** only the deck at `1.0` contributes to the cube, and a deck at `0.0` contributes
  nothing

#### Scenario: Raising a deck's volume fades its preset in

- **WHEN** a deck's volume is raised from `0` toward `1`
- **THEN** that deck's preset becomes proportionally brighter in the blended output

#### Scenario: Decks evolve independently

- **WHEN** two decks run different presets and are both audible
- **THEN** each advances its own colour evolution (the layers are visually distinct)

### Requirement: Engine exposes a buffer-targeted render alongside update

The visual engine SHALL provide a render entry point that composites its elements into a
**caller-supplied buffer** without applying master brightness or clipping, so the mixer can
weight and accumulate decks. The existing `update(model, t, features)` SHALL remain for the
standalone (single-engine) path and SHALL still apply master and clip.

#### Scenario: Mixer composites via render

- **WHEN** the mixer renders a deck
- **THEN** the engine writes that deck's element contribution into the provided buffer and the
  mixer applies the deck volume, then master and clip once for the final image

### Requirement: Global modulators shape every preset

The engine SHALL expose global modulators that all elements honor: **intensity** (overall
gain), **evolution speed** (hue drift rate and its acceleration, direction reversible),
**size** (spatial extent of moving/sparkle elements), **freeze** (hold the evolving palette),
and **mono** (render stark, desaturated/white). These SHALL be live-adjustable each frame.

#### Scenario: Freeze holds the palette

- **WHEN** freeze is enabled
- **THEN** the global hue evolution stops advancing until freeze is released

#### Scenario: Mono renders stark

- **WHEN** mono is enabled
- **THEN** elements render with zero saturation (white/greyscale) instead of their hues

#### Scenario: Intensity scales brightness

- **WHEN** intensity is reduced
- **THEN** the composited output is proportionally dimmer before master/clip
