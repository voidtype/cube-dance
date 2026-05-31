## ADDED Requirements

### Requirement: The panel shows per-deck presets and focus

The on-screen F1 SHALL label each fader with its **deck's current preset** and SHALL
highlight the **focused** deck. Touching a fader SHALL set focus to that deck. The display
SHALL show the focused deck's preset index, updated as the encoder scrolls.

#### Scenario: Touching a fader focuses its deck on the panel

- **WHEN** a fader is pressed on the panel
- **THEN** that deck becomes focused and is highlighted, and the display shows its preset

#### Scenario: Fader labels reflect deck presets

- **WHEN** a deck's preset changes
- **THEN** that fader's label updates to the new preset name
