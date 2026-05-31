## 1. Model

- [x] 1.1 `led_topology.py`: compute a per-pixel outward `normal` `(N,3)` — edge pixels out from the beam centre line, corner pixels out from the corner-cube centre; expose `model.normal`.
- [x] 1.2 `geometry.py`: add edge cross-section centre + the 2 outward face axes per edge (helpers for lacing + normals), if not already derivable.

## 2. Truss geometry

- [x] 2.1 `truss.py`: `cylinder(p0, p1, radius, sides)` → (positions, normals) low-poly hex tube.
- [x] 2.2 `truss.py`: edge beams — 4 chord tubes per edge over the lit run + diagonal lacing (zig-zag) on the 2 outward faces.
- [x] 2.3 `truss.py`: corner cubes — 12 frame-edge tubes per corner + X-brace diagonals on the 3 outward faces.
- [x] 2.4 `truss.py`: `build_truss(cfg)` → combined `(T,3)` positions + normals; tube radii/lacing configurable.

## 3. Rendering

- [x] 3.1 `render/scene.py`: metal program — grey base, ambient + Lambert diffuse + soft low Blinn-Phong specular + faint fresnel ("dull aluminium").
- [x] 3.2 `render/scene.py`: upload the truss mesh; draw it in the opaque pass (depth write) when `show_truss`.
- [x] 3.3 `render/scene.py`: offset the LED position VBO by `model.normal * (tube_radius + ε)` so LEDs sit on the tube surfaces; keep markers as-is.
- [x] 3.4 `config.py` / `cli.py`: `show_truss` (default True) + `--no-truss`.

## 4. Verify & document

- [x] 4.1 `tests/`: `model.normal` is unit-length and outward; `truss.build_truss` returns non-empty positions+normals with matching shapes; chord tubes near the LED chord lines.
- [x] 4.2 `uv run pytest` green; offscreen render (truss + LEDs) to eyeball dull-metal look and LEDs-on-tubes; watchdog-guarded.
- [x] 4.3 README: mention the truss + `--no-truss`.
- [x] 4.4 `openspec validate truss-structure --strict` passes.
