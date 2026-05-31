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

