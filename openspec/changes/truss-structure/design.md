## Context

The geometry module already knows each edge's 4 chord lines and each corner cube's edges
(the LED chords were built from them). The truss is the same lines rendered as tubes, so
the LEDs line up with the chords for free. The renderer has an opaque pass (depth-write)
for scenery and an additive pass (depth-test, no depth-write) for LEDs.

## Goals / Non-Goals

**Goals:** a believable dull-aluminium F34 frame (chords + face lacing + corner blocks)
beneath the LEDs, reacting to light; LEDs visibly on the tube surfaces; cheap enough to
stay at 60 FPS; toggleable.

**Non-Goals:** photoreal truss, accurate bolt/coupler detail, real reflections/GI, exact
F34 lacing pattern.

## Decisions

### D1 — Tubes from the existing chord/corner lines
`truss.py` generates a low-poly **hexagonal cylinder** between two points (positions +
normals). Per edge: 4 chord tubes (radius ~22 mm) over the lit run, plus **diagonal lacing**
(zig-zag tubes, ~13 mm) on the two outward faces — the visible "triangles". Per corner: the
12 corner-cube edge tubes plus X-brace diagonals on the 3 outward faces. All concatenated
into one `(T,3)` positions + normals mesh. Counts are a few hundred tubes (~tens of k
triangles) — trivial for the GPU.

### D2 — Dull-aluminium shading
A dedicated metal program: grey base (~0.55), ambient + Lambert diffuse from the existing
directional light, plus a **broad, low-intensity Blinn-Phong specular** (moderate exponent,
small weight) for a dull sheen that shifts as the camera moves — "reacts as such" without
looking chrome. A faint fresnel rim adds shape. No per-frame LED light sampling (too costly);
the constant directional light is enough to read as metal.

### D3 — LEDs on top of the tubes
Add `CubeModel.normal` — a per-pixel outward direction: edge pixels point out from the beam
centre line (in the cross-section plane); corner pixels point out from the corner-cube
centre. The scene uploads LED positions offset by `normal * (tube_radius + ε)`, so each LED
sits just outside its tube surface (lights on top of the truss), while `model.positions`
(used for the VU height etc.) is unchanged.

### D4 — Render order
Opaque pass (depth test + write): scenery, then truss (metal). Additive pass (depth test,
**no** depth-write): LEDs (offset) + markers. So the truss occludes LEDs behind it and the
near LEDs glow on top of their tubes; far LEDs still glow through the open frame gaps
(realistic for an open truss).

## Risks / Trade-offs

- **Z-fighting LED vs tube** → Mitigation: the outward offset (D3) puts LEDs clear of the
  surface.
- **Tube count / perf** → Mitigation: low-poly hex tubes, lacing only on outward faces, one
  combined draw; still a few-hundred tubes.
- **Can't see it live here** → Mitigation: offscreen render + eyeball; watchdog-guarded.

## Open Questions

- Lacing density/visible-faces and tube radii are tuned by eye; easy to adjust.
