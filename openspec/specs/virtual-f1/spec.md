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

