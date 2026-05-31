## ADDED Requirements

### Requirement: Render the truss as dull aluminium beneath the LEDs

The viewer SHALL render the truss structure as an **opaque dull-aluminium** material
(ambient + diffuse + a soft, low specular highlight that reacts to the light and camera)
drawn **beneath** the LEDs, and SHALL offset each LED onto the outer surface of its tube so
the lights read as mounted on the truss rather than buried in it. The **LEDs SHALL render
as additive emissive glow that is not occluded** — their brightness SHALL be consistent
regardless of camera angle (transparent through each other and through the open frame),
never flickering or dimming as the view rotates. The truss SHALL be toggleable.

#### Scenario: Truss sits under the lights

- **WHEN** the viewer renders with the truss enabled
- **THEN** the truss appears as an opaque metallic frame and the LEDs appear on its tube
  surfaces (not buried)

#### Scenario: LED brightness is view-independent

- **WHEN** the camera orbits to different angles around the cube
- **THEN** each LED's rendered brightness stays consistent (LEDs are additive and not
  occluded by the truss or by one another)

#### Scenario: Truss can be toggled off

- **WHEN** the truss is disabled in configuration
- **THEN** the truss is not rendered and the LEDs (and other scenery) still render correctly
