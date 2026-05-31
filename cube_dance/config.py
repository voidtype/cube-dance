"""Cube configuration derived from ``reference/whole_cube.scad``.

The SCAD model is in centimetres. We convert to metres, centre the cube on the
origin, and use +Y as up (the cube rests on the floor at ``y = -half``).
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Constants from reference/whole_cube.scad (SCAD units = cm) ---------------
SCAD_STICK_CM = 200.0  # stick_height: clear LED run per edge
SCAD_CORNER_CM = 30.0  # corner_cube_height: corner cube edge
SCAD_CORNER_EXTRA_CM = 4.1  # corner_extra_width: plate protrusion
SCAD_SIDE_CM = SCAD_STICK_CM + 2 * SCAD_CORNER_CM  # 260 cm = full cube side

AXIS_Y = 1  # +Y is up


@dataclass(frozen=True)
class CubeConfig:
    """Physical + LED parameters for the cube.

    All lengths are in metres. Geometry is centred on the origin with +Y up.
    """

    # Geometry (metres), derived from the SCAD constants by default.
    side_m: float = SCAD_SIDE_CM / 100.0  # 2.60
    edge_run_m: float = SCAD_STICK_CM / 100.0  # 2.00 (lit run per edge)
    corner_m: float = SCAD_CORNER_CM / 100.0  # 0.30 (corner cube edge)
    corner_extra_m: float = SCAD_CORNER_EXTRA_CM / 100.0  # 0.041 (plate)

    # Truss beam square cross-section side (F34 ~= 0.29 m; we align to the
    # 0.30 m corner cube so beams and corner blocks line up).
    beam_width_m: float = SCAD_CORNER_CM / 100.0  # 0.30

    # LED linear densities (LEDs per metre). Corners are denser on purpose.
    edge_leds_per_m: float = 60.0
    corner_leds_per_m: float = 120.0

    # How many of each corner's 3 outward faces carry an X panel (1..3).
    corner_x_faces: int = 3
    # Light the 12 edges of each corner cube (the glowing outline) in addition
    # to the X panels.
    corner_edges: bool = True

    # Optional scenery for realism (toggle with env/CLI; see app/cli).
    show_floor: bool = True  # clay ground plane
    show_speakers: bool = True  # speaker cabinets + their blue marker LEDs
    show_bushes: bool = True  # surrounding bushes (it's a bush doof)

    def __post_init__(self) -> None:
        if not (1 <= self.corner_x_faces <= 3):
            raise ValueError("corner_x_faces must be between 1 and 3")
        if self.edge_leds_per_m <= 0 or self.corner_leds_per_m <= 0:
            raise ValueError("LED densities must be positive")
        if self.corner_leds_per_m <= self.edge_leds_per_m:
            raise ValueError("corners must be denser than edges (corner > edge density)")

    # --- Derived geometry ----------------------------------------------------
    @property
    def half(self) -> float:
        """Half the full cube side; cube spans [-half, +half] on each axis."""
        return self.side_m / 2.0  # 1.30

    @property
    def edge_half(self) -> float:
        """Half the lit edge run; edge pixels span [-edge_half, +edge_half]."""
        return self.edge_run_m / 2.0  # 1.00

    def edge_pixel_count(self) -> int:
        """LED pixels along one chord-row of an edge beam."""
        return max(1, int(round(self.edge_leds_per_m * self.edge_run_m)))

    def corner_diagonal_pixel_count(self) -> int:
        """LED pixels along one diagonal of a corner X face."""
        diag_len = self.corner_m * 2.0**0.5
        return max(2, int(round(self.corner_leds_per_m * diag_len)))

    def corner_edge_pixel_count(self) -> int:
        """LED pixels along one edge of a corner cube."""
        return max(2, int(round(self.corner_leds_per_m * self.corner_m)))
