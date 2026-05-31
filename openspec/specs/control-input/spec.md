# control-input Specification

## Purpose
TBD - created by archiving change phase-3-f1-control. Update Purpose after archive.
## Requirements
### Requirement: F1 control model and parameter mapping

The system SHALL maintain a hardware-agnostic **control model** representing the Traktor F1:
4 **knobs** and 4 **faders** (each 0..1), named **buttons** (on/off), a 2-digit **display
value P** (0..99), a browse **encoder**, and 16 **pads**. A **mapping** SHALL apply the
control state to the visual/AGC parameters each frame: knobs and faders SHALL drive
continuous parameters, the encoder SHALL change P, and buttons SHALL toggle states. The
control model SHALL be writable by both the virtual panel and MIDI, interchangeably.

#### Scenario: A knob/fader drives its mapped parameter

- **WHEN** a knob (or fader) value is changed and the mapping is applied
- **THEN** its mapped visual/AGC parameter changes correspondingly

#### Scenario: Encoder changes the display value

- **WHEN** the encoder is stepped up or down
- **THEN** the display value P changes by the step and stays within `0..99` (wrapping)

#### Scenario: A button toggles

- **WHEN** a button is pressed twice
- **THEN** its state goes on then off

### Requirement: Basic Traktor F1 MIDI input

The system SHALL optionally read a connected **Traktor Kontrol F1** over MIDI and feed the
control model from it (control-change messages → knobs/faders, note messages → buttons), so
hardware and the virtual panel are interchangeable. If no F1 (or no MIDI backend) is present
it SHALL be a no-op and SHALL NOT error.

#### Scenario: No hardware present

- **WHEN** no F1 / MIDI input is available
- **THEN** the application runs normally and the virtual panel still controls the visuals

