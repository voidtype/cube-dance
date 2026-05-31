## ADDED Requirements

### Requirement: Render the truss as dull aluminium beneath the LEDs

The viewer SHALL render the truss structure as an **opaque dull-aluminium** material
(ambient + diffuse + a soft, low specular highlight that reacts to the light and camera)
drawn **beneath** the LEDs, and SHALL offset each LED onto the outer surface of its tube so
the lights read as mounted on the truss rather than buried in it. The LEDs are additive
emissive: opaque geometry in front of an LED (the near side of the truss, speakers, the
ground) SHALL occlude it for realism, but an LED SHALL NOT be occluded by the very tube it
is mounted on (no view-angle flicker), and LEDs SHALL NOT occlude one another (they remain
transparent/additive). The truss SHALL be toggleable.

#### Scenario: Truss sits under the lights

- **WHEN** the viewer renders with the truss enabled
- **THEN** the truss appears as an opaque metallic frame and the LEDs appear on its tube
  surfaces (not buried)

#### Scenario: Opaque geometry occludes LEDs

- **WHEN** an opaque object (a speaker, or the near side of the truss) is between the
  camera and an LED
- **THEN** that LED is hidden behind it

#### Scenario: No self-occlusion flicker

- **WHEN** the camera rotates around the cube
- **THEN** the camera-facing LEDs stay consistently lit — they are not flickered or dimmed
  by the tubes they are mounted on, and LEDs do not occlude one another

#### Scenario: Truss can be toggled off

- **WHEN** the truss is disabled in configuration
- **THEN** the truss is not rendered and the LEDs (and other scenery) still render correctly
