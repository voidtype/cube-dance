## ADDED Requirements

### Requirement: The panel reflects the deck mixer and performance surface

The on-screen F1 SHALL label each fader with its **channel's preset** and highlight the
**selected** channel (its bottom-row button lit). The knobs SHALL show the **selected
channel's** preset param labels. Each pad SHALL be tinted with its **trigger's colour** and
glow when hit. The 7-segment display SHALL show the selected channel's preset index.

#### Scenario: Selecting a channel updates the panel

- **WHEN** a bottom-row channel button is pressed
- **THEN** that channel is highlighted, the knob labels switch to its preset, and the display
  shows its preset index

#### Scenario: Pads show preset trigger colours

- **WHEN** a preset is loaded on a channel
- **THEN** that column's pads are drawn in the preset's per-trigger colours

#### Scenario: Hitting a pad fires its trigger

- **WHEN** a pad is clicked
- **THEN** the panel queues that (column, row) trigger for the app to fire and the pad glows
