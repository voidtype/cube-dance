## ADDED Requirements

### Requirement: Render the truss as dull aluminium beneath the LEDs

The viewer SHALL render the truss structure as an **opaque dull-aluminium** material
(ambient + diffuse + a soft, low specular highlight that reacts to the light and camera)
drawn **beneath** the LEDs, and SHALL offset each LED onto the outer surface of its tube so
the lights read as mounted on the truss rather than buried in it. The truss SHALL be
occlusion-correct (it hides LEDs directly behind it) and SHALL be toggleable.

#### Scenario: Truss sits under the lights

- **WHEN** the viewer renders with the truss enabled
- **THEN** the truss appears as an opaque metallic frame, the LEDs appear on its tube
  surfaces (not buried), and the truss occludes LEDs directly behind it

#### Scenario: Truss can be toggled off

- **WHEN** the truss is disabled in configuration
- **THEN** the truss is not rendered and the LEDs (and other scenery) still render correctly
