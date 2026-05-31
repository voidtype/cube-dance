## ADDED Requirements

### Requirement: Render the truss as dull aluminium beneath the LEDs

The viewer SHALL render the truss structure as an **opaque dull-aluminium** material
(ambient + diffuse + a soft, low specular highlight that reacts to the light and camera)
drawn beneath the LEDs. The **LEDs SHALL be rendered as emissive solid geometry** — a thin
tube along each LED run, sitting on the outer surface of the truss tube and coloured
per-pixel from the LED color buffer — **not** as point sprites. Because the LEDs are solid
geometry with proper per-fragment depth, their brightness SHALL be **independent of the
view angle** (no sprite-density or single-depth popping artifacts), and opaque geometry in
front of an LED (the near side of the truss, speakers, the ground) SHALL occlude it
correctly. The truss SHALL be toggleable.

#### Scenario: Truss sits under the lights

- **WHEN** the viewer renders with the truss enabled
- **THEN** the truss appears as an opaque metallic frame and the LED tubes appear on its
  outer surfaces (mounted on it, not buried)

#### Scenario: Opaque geometry occludes LEDs

- **WHEN** an opaque object (a speaker, or the near side of the truss) is between the
  camera and an LED
- **THEN** that LED is hidden behind it

#### Scenario: LED brightness is view-independent

- **WHEN** the camera rotates around the cube (e.g. viewing a corner X panel from many
  angles, including low/grazing ones)
- **THEN** every LED run stays consistently lit — neither X diagonal becomes brighter or
  dimmer than the other with the angle, and no LED line flickers or dims as the view moves

#### Scenario: Truss can be toggled off

- **WHEN** the truss is disabled in configuration
- **THEN** the truss is not rendered and the LEDs (and other scenery) still render correctly
