## ADDED Requirements

### Requirement: Faders are per-channel preset volumes

The four F1 faders SHALL act as the **volumes of the four mixer channels** (fader _i_
controls channel _i_). Raising a fader SHALL fade that channel's preset into the blended
output; lowering it to zero SHALL remove it.

#### Scenario: Fader drives channel volume

- **WHEN** fader 2 is moved
- **THEN** channel 2's contribution to the cube scales with the fader position

### Requirement: Pads are per-channel preset triggers

The 4×4 pad grid SHALL map **one column per channel**; the four pads in a column SHALL be
that channel's preset **triggers**. Hitting a pad SHALL fire the corresponding trigger on
that channel, and each pad SHALL show its trigger's **colour annotation**.

#### Scenario: A pad fires its channel's trigger

- **WHEN** a pad in column 3 is hit
- **THEN** the corresponding trigger of channel 3's preset fires (an accent on that channel)

#### Scenario: Pads carry preset colours

- **WHEN** a preset is loaded on a channel
- **THEN** that column's pads display the preset's per-trigger colours (not a fixed palette)

### Requirement: QUANT quantises triggers to the beat

When `QUANT` is enabled, a pad hit SHALL be deferred and fired on the next detected beat
(a detected kick or a beat-phase wrap), with a short timeout fallback so it still fires if
no beat is detected.

#### Scenario: Quantised trigger waits for the beat

- **WHEN** `QUANT` is on and a pad is hit between beats
- **THEN** the trigger fires on the next beat rather than immediately

### Requirement: The bottom row selects the channel; the encoder cycles its preset

A **bottom-row** button SHALL select its channel (the one the knobs and encoder act on), and
the **browse encoder** SHALL cycle the **selected channel's** preset, shown on the 7-segment
display. A keyboard key SHALL cycle it the same way.

#### Scenario: Select a channel then change its preset

- **WHEN** a bottom-row button is pressed and then the encoder is scrolled
- **THEN** that channel becomes selected and its preset advances through the built-in list

### Requirement: Knobs are the selected channel's preset params

The four knobs SHALL drive the **selected channel's** preset **params** (intensity, hue,
evolution speed, spatial size), using the **labels and defaults declared by that preset**.
Selecting a different channel SHALL load that channel's current param values onto the knobs.

#### Scenario: A knob changes the selected channel

- **WHEN** a knob is turned
- **THEN** the selected channel's corresponding param changes (other channels are unaffected)

#### Scenario: Knob labels follow the preset

- **WHEN** a channel's preset changes
- **THEN** the knob labels reflect the new preset's declared params

### Requirement: Function buttons set global performance flags

The remaining function buttons SHALL set global flags applied across all channels: `TYPE`
mono/stark, `SHIFT` freeze, `REVERSE` reverse colour drift, `SIZE` fatten, `SYNC` beat-pulse
the rig, `CAPTURE` blackout, `BROWSE` reset the selected channel's knobs to preset defaults.

#### Scenario: Mono button starkens the look

- **WHEN** `TYPE` is enabled
- **THEN** the blended output renders desaturated (stark white) across all channels

#### Scenario: Blackout kills output

- **WHEN** `CAPTURE` is enabled
- **THEN** the cube goes dark until it is released
