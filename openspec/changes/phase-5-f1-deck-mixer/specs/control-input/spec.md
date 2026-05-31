## ADDED Requirements

### Requirement: Faders are per-deck preset volumes

The four F1 faders SHALL act as the **volumes of the four mixer decks** (fader _i_ controls
deck _i_). Raising a fader SHALL fade that deck's preset into the blended output; lowering it
to zero SHALL remove it.

#### Scenario: Fader drives deck volume

- **WHEN** fader 2 is moved
- **THEN** deck 2's contribution to the cube scales with the fader position

### Requirement: The browse encoder selects the focused deck's preset

The deck whose fader was **last touched** SHALL be the **focused** deck. The browse encoder
SHALL cycle the focused deck's preset through the built-in preset order, and the 7-segment
display SHALL show the focused deck's preset index. A keyboard key SHALL cycle it the same way.

#### Scenario: Encoder changes the focused deck's preset

- **WHEN** a fader is touched and then the encoder is scrolled
- **THEN** that deck's preset advances through the built-in list and the display updates

#### Scenario: Focus follows the touched fader

- **WHEN** a different fader is touched
- **THEN** focus moves to that deck and the display shows that deck's current preset

### Requirement: Knobs and buttons shape the presets globally

The four knobs SHALL map to **global modulators** applied to every deck: intensity, evolution
speed, size, and hide-quiet (AGC presence). Buttons SHALL toggle global looks: `REVERSE`
flips the evolution direction, `SHIFT` freezes evolution, `TYPE` switches to stark/mono,
`SIZE` boosts size. Changes SHALL take effect live.

#### Scenario: A knob changes all decks

- **WHEN** the evolution-speed knob is turned
- **THEN** every audible deck's colour evolution speeds up or slows down together

#### Scenario: Mono button starkens the look

- **WHEN** `TYPE` is enabled
- **THEN** the blended output renders desaturated (stark white) across all decks
