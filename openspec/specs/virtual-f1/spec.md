# virtual-f1 Specification

## Purpose
TBD - created by archiving change phase-3-f1-control. Update Purpose after archive.
## Requirements
### Requirement: Interactive on-screen F1 panel

The system SHALL render an on-screen **virtual Traktor F1**, modelled on the real unit, as
an overlay in the **right quarter** of the window. Its **knobs and faders SHALL be
click-and-drag** widgets (dragging changes the value, VST-style). Its **buttons SHALL be
grey by default and light up when clicked** (toggling their control state). It SHALL show a
**digital (7-segment-style) display** of the value P, with the browse **encoder** beside it
changing P when scrolled, and SHALL show the 4×4 **pads** styled like the unit. Driving a
widget SHALL update the underlying control model (and thus the mapped parameters).

#### Scenario: Dragging a knob or fader

- **WHEN** the user drags a knob or fader on the panel
- **THEN** that control's value changes and its mapped parameter updates

#### Scenario: Clicking a button lights it

- **WHEN** the user clicks a button
- **THEN** it lights up and its control state turns on; clicking again unlights it

#### Scenario: Scrolling the encoder updates the display

- **WHEN** the user scrolls over the browse encoder
- **THEN** the display value P changes and the digital display reflects it

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

