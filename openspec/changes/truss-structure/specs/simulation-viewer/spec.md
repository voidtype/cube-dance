## ADDED Requirements

### Requirement: Render the truss as dull aluminium beneath the LEDs

The viewer SHALL render the truss structure as an **opaque dull-aluminium** material
(ambient + diffuse + a soft, low specular highlight that reacts to the light and camera)
drawn **beneath** the LEDs, and SHALL offset each LED onto the outer surface of its tube so
the lights read as mounted on the truss rather than buried in it. LED brightness SHALL be
**independent of the viewing angle**: it SHALL NOT change with how densely the LED sprites
overlap on screen (achieved by max-blending rather than additive summing) and an LED SHALL
NOT be occluded by, or flicker against, the tube it is mounted on. Opaque geometry in front
of an LED (the near side of the truss, speakers, the ground) SHALL still occlude it for
realism. The truss SHALL be toggleable.

#### Scenario: Truss sits under the lights

- **WHEN** the viewer renders with the truss enabled
- **THEN** the truss appears as an opaque metallic frame and the LEDs appear on its tube
  surfaces (not buried)

#### Scenario: Opaque geometry occludes LEDs

- **WHEN** an opaque object (a speaker, or the near side of the truss) is between the
  camera and an LED
- **THEN** that LED is hidden behind it

#### Scenario: LED brightness is view-independent

- **WHEN** the camera rotates around the cube (e.g. viewing a corner X panel from
  different angles)
- **THEN** each LED line stays consistently lit — no diagonal becomes brighter or dimmer
  than the other with the angle, and LEDs do not flicker against their tubes (brightness
  does not depend on sprite overlap because LEDs are max-blended, not additively summed)

#### Scenario: Truss can be toggled off

- **WHEN** the truss is disabled in configuration
- **THEN** the truss is not rendered and the LEDs (and other scenery) still render correctly
