## ADDED Requirements

### Requirement: Truss structural geometry

The model SHALL provide truss structural geometry derived from the F34 box truss: for each
of the 12 edges, the **4 chord lines** plus **diagonal lacing** on the outward faces; and
for each of the 8 corners, the **corner-cube frame edges** plus X bracing. It SHALL be
expressed as tube (cylinder) meshes in metres, aligned so the edge LED chord rows lie on
the chord tubes.

#### Scenario: Chords align with the LED rows

- **WHEN** the truss geometry is built
- **THEN** each edge's chord tubes are coincident (within the tube radius) with that edge's
  LED chord lines, so the LEDs sit on the chords

#### Scenario: Corner frames present

- **WHEN** the truss geometry is built
- **THEN** every one of the 8 corners contributes the 12 tubes of its corner-cube frame

### Requirement: Per-pixel outward orientation

The model SHALL expose a per-pixel **outward unit normal** aligned to the pixel index
(shape `(N, 3)`), used to seat each LED on the outer surface of its tube: for **edge**
pixels the normal points radially out from that beam's chord-bundle centre line
(perpendicular to the edge run); for **corner** pixels it points out from the corner-cube
centre.

#### Scenario: Normals are unit-length and seat LEDs outward

- **WHEN** the model is built
- **THEN** every pixel's normal has unit length; each edge pixel's normal is perpendicular
  to its edge run and points away from that beam's centre line; each corner pixel's normal
  points away from its corner-cube centre
