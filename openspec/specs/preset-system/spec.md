# preset-system Specification

## Purpose
TBD - created by archiving change phase-4-visual-dsl. Update Purpose after archive.
## Requirements
### Requirement: Python presets compose the visual

The system SHALL define visuals as **Python presets** — modules exposing a `build(engine)`
that instantiates elements and wires their event subscriptions and modulators. Presets
SHALL be **selectable by name**, with built-in presets shipped in the package. Selecting an
unknown preset SHALL raise a clear error.

#### Scenario: A named preset builds its elements

- **WHEN** a built-in preset is selected and built
- **THEN** the engine contains that preset's elements and runs them

#### Scenario: Unknown preset errors

- **WHEN** a preset name with no matching module is selected
- **THEN** a clear error is raised (and the app can fall back to a default)

### Requirement: An ordered built-in preset list backs deck selection

The preset system SHALL expose an **ordered list** of built-in presets that the deck mixer
and the browse encoder cycle through. The list SHALL include at least `deep`, `punchy`,
`minimal`, and `strobe` (and MAY include stylistically distinct presets such as `inferno`,
`matrix`, `plasma`, `siren`), and selecting an index SHALL load that preset onto a deck.

#### Scenario: Encoder cycles the built-in order

- **WHEN** the encoder advances past the last preset
- **THEN** it wraps to the first preset in the order

#### Scenario: Decks start on distinct presets

- **WHEN** the mixer is created
- **THEN** the four decks are loaded with distinct built-in presets

### Requirement: A preset declares its performance surface

A preset SHALL be able to declare a **performance schema**: `KNOBS` (up to four knob params,
each a label + driven effect + default) and `TRIGGERS` (up to four pad triggers, each a
label, a colour, and a factory that returns a transient element). Loading a preset SHALL
apply this schema to the deck; absent declarations SHALL fall back to sensible defaults.

#### Scenario: Loading a preset configures the surface

- **WHEN** a preset declaring `KNOBS` and `TRIGGERS` is loaded on a deck
- **THEN** that deck's knob labels/defaults and pad trigger colours/behaviours come from the
  preset

#### Scenario: A trigger is arbitrary preset code

- **WHEN** a pad trigger fires
- **THEN** the preset's factory runs and returns a transient element of its choosing (stab,
  riser, strobe, sparkle, …)

