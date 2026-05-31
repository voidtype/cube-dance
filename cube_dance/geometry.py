"""Structural geometry of the cube: the 12 edge beams and 8 corner cubes.

Coordinates are in metres, centred on the origin, +Y up. This module is the
single source of truth for the deterministic ordering of edges and corners that
the LED addressing in :mod:`cube_dance.led_topology` relies on.

Each main edge is a square-section truss beam: LEDs run along its *chords* (the
long edges of that square section), giving two rows per visible face. Base edges
(bottom square) only light their outward vertical face -- the ground-facing and
up-facing rows would be invisible or stepped on. Each corner is a 0.30 m cube
whose 12 edges are lit (the glowing outline) plus X panels on its outward faces.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import AXIS_Y, CubeConfig

# Deterministic corner ordering: index 0..7 over (sx, sy, sz) in {-1, +1}.
CORNER_SIGNS: tuple[tuple[int, int, int], ...] = tuple(
    (sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
)

# Deterministic edge ordering: 4 edges per axis, axis = 0(X), 1(Y), 2(Z).
_EDGE_FIXED = ((-1, -1), (-1, 1), (1, -1), (1, 1))


@dataclass(frozen=True)
class Edge:
    index: int
    axis: int  # 0=X, 1=Y, 2=Z (the axis the edge runs along)
    fixed: tuple[int, int]  # outward signs on the two other dims (ascending)


@dataclass(frozen=True)
class Corner:
    index: int
    signs: tuple[int, int, int]  # (sx, sy, sz)


def build_edges() -> list[Edge]:
    edges: list[Edge] = []
    idx = 0
    for axis in (0, 1, 2):
        for fixed in _EDGE_FIXED:
            edges.append(Edge(index=idx, axis=axis, fixed=fixed))
            idx += 1
    return edges


def build_corners() -> list[Corner]:
    return [Corner(index=i, signs=s) for i, s in enumerate(CORNER_SIGNS)]


def _other_axes(axis: int) -> tuple[int, int]:
    return tuple(d for d in (0, 1, 2) if d != axis)  # type: ignore[return-value]


def is_base_edge(edge: Edge) -> bool:
    """True for the 4 bottom-square edges (a perpendicular -Y, i.e. on the floor)."""
    d0, d1 = _other_axes(edge.axis)
    for dim, sign in ((d0, edge.fixed[0]), (d1, edge.fixed[1])):
        if dim == AXIS_Y and sign < 0:
            return True
    return False


def edge_endpoints(edge: Edge, cfg: CubeConfig, *, full: bool = False) -> np.ndarray:
    """Centre-line endpoints of an edge as ``(2, 3)`` (for the reference frame)."""
    span = cfg.half if full else cfg.edge_half
    d0, d1 = _other_axes(edge.axis)
    a = np.zeros(3)
    b = np.zeros(3)
    a[edge.axis], b[edge.axis] = -span, span
    a[d0] = b[d0] = edge.fixed[0] * cfg.half
    a[d1] = b[d1] = edge.fixed[1] * cfg.half
    return np.stack([a, b])


def edge_chord_rows(edge: Edge, cfg: CubeConfig) -> list[tuple[np.ndarray, np.ndarray]]:
    """Lit chord rows for an edge beam, as (p0, p1) endpoint pairs.

    The beam's square section has 4 chords (at inner ``edge_half`` and outer
    ``half`` offsets on the two perpendicular axes). A chord is lit if it lies on
    an *included* outward face. Both outward faces are included, except a
    downward (-Y) face on a base edge, which is dropped.
    """
    axis = edge.axis
    d0, d1 = _other_axes(axis)
    s0, s1 = edge.fixed
    eh, h = cfg.edge_half, cfg.half

    include0 = not (d0 == AXIS_Y and s0 < 0)
    include1 = not (d1 == AXIS_Y and s1 < 0)

    rows: list[tuple[np.ndarray, np.ndarray]] = []
    for c0 in (s0 * eh, s0 * h):
        for c1 in (s1 * eh, s1 * h):
            on_face = (include0 and abs(c0 - s0 * h) < 1e-9) or (
                include1 and abs(c1 - s1 * h) < 1e-9
            )
            if not on_face:
                continue
            p0, p1 = np.zeros(3), np.zeros(3)
            p0[axis], p1[axis] = -eh, eh
            p0[d0] = p1[d0] = c0
            p0[d1] = p1[d1] = c1
            rows.append((p0, p1))
    return rows


def corner_cube_edges(corner: Corner, cfg: CubeConfig) -> list[tuple[np.ndarray, np.ndarray]]:
    """The 12 edges of a corner cube (outer 0.30 m region) as endpoint pairs."""
    s = corner.signs
    eh, h = cfg.edge_half, cfg.half
    bounds = [(s[k] * eh, s[k] * h) for k in range(3)]  # (inner, outer) per axis

    def v(ix: int, iy: int, iz: int) -> np.ndarray:
        return np.array([bounds[0][ix], bounds[1][iy], bounds[2][iz]])

    edges: list[tuple[np.ndarray, np.ndarray]] = []
    for iy in (0, 1):
        for iz in (0, 1):
            edges.append((v(0, iy, iz), v(1, iy, iz)))  # along X
    for ix in (0, 1):
        for iz in (0, 1):
            edges.append((v(ix, 0, iz), v(ix, 1, iz)))  # along Y
    for ix in (0, 1):
        for iy in (0, 1):
            edges.append((v(ix, iy, 0), v(ix, iy, 1)))  # along Z
    return edges


def corner_x_faces(
    corner: Corner, cfg: CubeConfig
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """X-panel diagonals on a corner's outward faces.

    Returns ``(p0, p1, face_normal)`` per diagonal. ``face_normal`` is the face's
    outward axis unit vector, used to lift the X LEDs straight out of the face
    (keeping both diagonals coplanar so they can't occlude each other).
    """
    signs = corner.signs
    inner, outer = cfg.edge_half, cfg.half
    segments: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    for face_axis in range(cfg.corner_x_faces):
        d0, d1 = _other_axes(face_axis)
        face_coord = signs[face_axis] * outer
        normal = np.zeros(3)
        normal[face_axis] = float(signs[face_axis])

        def pt(c0: float, c1: float) -> np.ndarray:
            p = np.zeros(3)
            p[face_axis] = face_coord
            p[d0] = c0
            p[d1] = c1
            return p

        lo0, hi0 = signs[d0] * inner, signs[d0] * outer
        lo1, hi1 = signs[d1] * inner, signs[d1] * outer
        a, b, c, d = pt(lo0, lo1), pt(hi0, lo1), pt(hi0, hi1), pt(lo0, hi1)
        segments.append((a, c, normal))
        segments.append((b, d, normal))
    return segments


def structure_line_vertices(cfg: CubeConfig) -> np.ndarray:
    """Faint reference frame: the 12 full edges, as ``(M, 3)`` GL LINES pairs."""
    verts = [edge_endpoints(edge, cfg, full=True) for edge in build_edges()]
    return np.concatenate(verts, axis=0).astype(np.float32)


def bounding_box(cfg: CubeConfig) -> tuple[np.ndarray, np.ndarray]:
    h = cfg.half
    return np.array([-h, -h, -h]), np.array([h, h, h])
