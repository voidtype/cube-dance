## ADDED Requirements

### Requirement: An ordered built-in preset list backs deck selection

The preset system SHALL expose an **ordered list** of built-in presets that the deck mixer
and the browse encoder cycle through. The list SHALL include at least `deep`, `punchy`,
`minimal`, and `strobe`, and selecting an index SHALL load that preset onto a deck.

#### Scenario: Encoder cycles the built-in order

- **WHEN** the encoder advances past the last preset
- **THEN** it wraps to the first preset in the order

#### Scenario: Decks start on distinct presets

- **WHEN** the mixer is created
- **THEN** the four decks are loaded with distinct built-in presets
