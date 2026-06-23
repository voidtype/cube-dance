"""Place each real fixture's pixels onto the physical cube geometry (Phase 3).

We anchor every fixture at its cube vertex and lay its LEDs along a segment of the
*idealised* geometry (:mod:`cube_dance.geometry`) — so the real, sparse hardware
inherits faithful 3-D positions and outward normals from the very model the
simulator already uses. This rests on the standing assumption that the repo's cube
geometry is close-correct and should stay stable.

The fixture→segment correspondence is derived from the fixture's ``cubeSection``,
its name, and its vertex:

* **Corner panels** (CLeft / CRight / CTop) sit on a corner's three outward faces.
  Each face carries an X (two diagonals) plus three frame edges (top/left/bot).
  We assign CLeft→X-face, CRight→Z-face, CTop→Y(up)-face.
* **Edge accents** (Left-/Right-/Top-N) are short strips running inward from the
  vertex along a cube edge.

Where the exact physical face/edge correspondence can only truly be settled on the
real cube, the choice here is a documented, internally-consistent assumption.
Because everything is anchored at the (known) vertex, geometry-aware effects still
read sensibly even if a face assignment is later flipped — and flips are a data
change (which face index a panel maps to), not a code rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import AXIS_Y, CubeConfig
from ..geometry import Corner, Edge, _other_axes, build_corners, build_edges
from .mapping import MappedFixture

GROUP_EDGE = np.uint8(0)
GROUP_CORNER = np.uint8(1)

# CLeft / CRight / CTop -> which outward face axis (0=X, 1=Y/up, 2=Z) of the corner.
_FACE_AXIS = {"left": 0, "right": 2, "top": 1}

# (axis, fixed signs) -> edge index, for resolving an accent's cube edge.
_EDGE_INDEX = {(e.axis, e.fixed): e.index for e in build_edges()}

# Structural sections grouped by which of the cube's 12 edges they ride. The
# beams/columns get best-guess placement: each fixture becomes a strip running
# the full 2 m between corners, with siblings as parallel lines across the beam
# face. Section -> edge group ("top"/"bottom"/"vertical"). Speculative.
_BEAM_GROUP = {
    "horizontal_top": "top", "horizontal_bar_top": "top",
    "horizontal_bottom": "bottom", "horizontal_bar_bottom": "bottom",
    "column": "vertical", "corner_inside": "vertical", "corner_outside": "vertical",
}


@dataclass(frozen=True)
class Placement:
    """A fixture's resolved geometry: per-pixel positions + normals + identity."""

    positions: np.ndarray  # (k, 3) float32, metres, centred
    normals: np.ndarray    # (k, 3) float32, outward unit
    group: int             # GROUP_EDGE / GROUP_CORNER
    element_id: int        # edge 0..11 or corner 0..7


def _sample(p0: np.ndarray, p1: np.ndarray, k: int, reverse: bool) -> tuple[np.ndarray, np.ndarray]:
    """``k`` points from p0→p1 (reversed if the strip is wired the other way)."""
    t = np.linspace(0.0, 1.0, k, dtype=np.float32)
    if reverse:
        t = t[::-1].copy()
    pts = p0[None, :] + t[:, None] * (p1 - p0)[None, :]
    return pts.astype(np.float32), t


def _face_segments(corner: Corner, face_axis: int, cfg: CubeConfig) -> dict[str, tuple]:
    """Named segments of one outward face of a corner cube.

    Returns ``{name: (p0, p1, normal)}`` for the X diagonals and frame edges of the
    square face at ``face_axis``'s outer offset.
    """
    s = corner.signs
    inner, outer = cfg.edge_half, cfg.half
    d0, d1 = (d for d in (0, 1, 2) if d != face_axis)
    normal = np.zeros(3, dtype=np.float64)
    normal[face_axis] = float(s[face_axis])

    def pt(c0: float, c1: float) -> np.ndarray:
        p = np.zeros(3)
        p[face_axis] = s[face_axis] * outer
        p[d0], p[d1] = c0, c1
        return p

    lo0, hi0 = s[d0] * inner, s[d0] * outer
    lo1, hi1 = s[d1] * inner, s[d1] * outer
    a, b, c, d = pt(lo0, lo1), pt(hi0, lo1), pt(hi0, hi1), pt(lo0, hi1)
    return {
        "diag-left": (a, c, normal),
        "diag-right": (b, d, normal),
        "bot": (a, b, normal),
        "right": (b, c, normal),
        "top": (d, c, normal),
        "left": (a, d, normal),
    }


def _place_corner(mf: MappedFixture, corner: Corner, cfg: CubeConfig) -> Placement:
    name, sec = mf.raw.name, mf.raw.section
    # cubeSection looks like corner_<face>_<part> (e.g. corner_left_diag).
    parts = sec.split("_")
    face_key = parts[1] if len(parts) > 1 else "left"
    part_key = parts[2] if len(parts) > 2 else "diag"
    face_axis = _FACE_AXIS.get(face_key, 0)
    segs = _face_segments(corner, face_axis, cfg)

    if part_key == "diag":
        seg_name = "diag-right" if "diag-right" in name else "diag-left"
    elif part_key in segs:
        seg_name = part_key
    else:
        seg_name = "diag-left"
    p0, p1, normal = segs[seg_name]

    k = mf.raw.led_count
    pts, _ = _sample(p0, p1, k, mf.assoc.reverse)
    nrm = np.tile(normal.astype(np.float32), (k, 1))
    return Placement(pts, nrm, GROUP_CORNER, int(mf.assoc.element_id if mf.assoc.element_id is not None else corner.index))


def _place_accent(mf: MappedFixture, corner: Corner, cfg: CubeConfig) -> Placement:
    """A short strip running inward from the vertex along a cube edge."""
    s = corner.signs
    inner, outer = cfg.edge_half, cfg.half
    sec = mf.raw.section
    k = mf.raw.led_count

    if sec == "vertical_top":   # Top-N: along the top X edge, on the up face
        axis, fixed = 0, (s[1], s[2])
        p_out = np.array([s[0] * outer, s[1] * outer, s[2] * inner])
        p_in = np.array([s[0] * inner, s[1] * outer, s[2] * inner])
        normal = np.array([0.0, float(s[1]), 0.0])
    elif sec == "vertical_right":  # Right-N: vertical strip on the Z face
        axis, fixed = 1, (s[0], s[2])
        p_out = np.array([s[0] * inner, s[1] * outer, s[2] * outer])
        p_in = np.array([s[0] * inner, s[1] * inner, s[2] * outer])
        normal = np.array([0.0, 0.0, float(s[2])])
    else:  # vertical_left (Left-N): vertical strip on the X face
        axis, fixed = 1, (s[0], s[2])
        p_out = np.array([s[0] * outer, s[1] * outer, s[2] * inner])
        p_in = np.array([s[0] * outer, s[1] * inner, s[2] * inner])
        normal = np.array([float(s[0]), 0.0, 0.0])

    edge_id = _EDGE_INDEX.get((axis, fixed))
    if edge_id is None:  # shouldn't happen; fall back to any edge on this axis
        edge_id = next(e.index for e in build_edges() if e.axis == axis)
    pts, _ = _sample(p_out, p_in, k, mf.assoc.reverse)
    nrm = np.tile(normal.astype(np.float32), (k, 1))
    return Placement(pts, nrm, GROUP_EDGE, int(edge_id))


# --- Beam / column strips (best-guess full-cube structure) ------------------
def _classify_edges(cfg: CubeConfig) -> dict[str, list[Edge]]:
    """The 12 cube edges split into top / bottom horizontals and verticals."""
    edges = build_edges()
    top, bottom, vertical = [], [], []
    for e in edges:
        if e.axis == 1:  # Y axis -> vertical
            vertical.append(e)
            continue
        # a horizontal edge's Y-sign lives in whichever fixed dim is the Y axis.
        d0, d1 = _other_axes(e.axis)
        sy = e.fixed[0] if d0 == AXIS_Y else e.fixed[1]
        (top if sy > 0 else bottom).append(e)
    key = lambda e: e.index
    return {"top": sorted(top, key=key), "bottom": sorted(bottom, key=key),
            "vertical": sorted(vertical, key=key)}


# Each beam/column FACE carries 2 LED strips, inset ~1 inch from the face edges
# (confirmed from reference photos). The beam's square section spans edge_half..
# half (0.30 m) on each perpendicular axis.
BEAM_INSET_M = 0.025  # ~1 inch


def _beam_face_strips(edge: Edge, cfg: CubeConfig) -> list[tuple]:
    """The LED strips on a beam/column: 2 per CLAD face, inset from the edges.

    From Luke's reference photos, every clad face has two parallel strips inset
    ~2.5 cm from each edge, and the clad faces differ by beam type:
      * Bottom beams: top (up, into the cube) + outward faces only -> 4 strips.
        The ground face and the INWARD face are bare.
      * Top beams: bottom (down, into the cube) + outward + inward faces -> 6.
        Only the skyward top face is bare.
      * Columns: all 4 faces visible -> 8 strips.
    Returns the strips (p0, p1, normal) ordered slot-major, so a beam with fewer
    fixtures than strips still spreads across its faces rather than filling one.
    """
    axis = edge.axis
    d0, d1 = _other_axes(axis)
    s0, s1 = edge.fixed
    eh, h = cfg.edge_half, cfg.half
    inset = BEAM_INSET_M

    # For a horizontal beam one perpendicular dim is Y (vertical), the other is
    # the horizontal "H" dim. A column's axis IS Y, so it has no Y-perp face.
    y_dim = y_sign = h_dim = None
    if d0 == AXIS_Y:
        y_dim, y_sign, h_dim = d0, s0, d1
    elif d1 == AXIS_Y:
        y_dim, y_sign, h_dim = d1, s1, d0

    faces = []  # (fixed_dim, fixed_val, outward_sign, vary_dim, vary_sign)
    for (fd, fs), (vd, vs) in (((d0, s0), (d1, s1)), ((d1, s1), (d0, s0))):
        for fixed_val, outward in ((fs * h, fs), (fs * eh, -fs)):  # outer, then inner
            is_outer = outward == fs
            if fd == y_dim and is_outer:  # outer Y face -> ground/sky, unclad
                continue
            # A bottom beam also leaves its INWARD (inner horizontal) face bare.
            if y_sign is not None and y_sign < 0 and fd == h_dim and not is_outer:
                continue
            faces.append((fd, fixed_val, outward, vd, vs))

    by_slot: list[list[tuple]] = [[], []]
    for fd, fixed_val, outward, vd, vs in faces:
        for slot, var_val in enumerate((vs * (eh + inset), vs * (h - inset))):
            p0, p1 = np.zeros(3), np.zeros(3)
            p0[axis], p1[axis] = -eh, eh
            p0[fd] = p1[fd] = fixed_val
            p0[vd] = p1[vd] = var_val
            normal = np.zeros(3)
            normal[fd] = float(outward)
            by_slot[slot].append((p0, p1, normal))
    return by_slot[0] + by_slot[1]


def assign_beam_strips(fixtures, cfg: CubeConfig) -> dict[str, tuple]:
    """Map each structural fixture -> (edge, strip_index, strip_count).

    Best-guess: within each group, fixtures sharing a vertex become the parallel
    strips of one beam, and the group's vertices are zipped onto its edges in
    index order. Deterministic (sorted by name). Confirmed at the integration test.
    """
    edge_groups = _classify_edges(cfg)
    by_group: dict[str, list] = {}
    for f in fixtures:
        g = _BEAM_GROUP.get(f.raw.section)
        if g is not None:
            by_group.setdefault(g, []).append(f)

    result: dict[str, tuple] = {}
    for gname, members in by_group.items():
        edges = edge_groups[gname]
        by_vertex: dict[int | None, list] = {}
        for f in members:
            by_vertex.setdefault(f.raw.vertex, []).append(f)
        for i, vtx in enumerate(sorted(by_vertex, key=lambda v: (v is None, v))):
            edge = edges[i % len(edges)]
            n_strips = len(_beam_face_strips(edge, cfg))  # 6 (beam) or 8 (column)
            strips = sorted(by_vertex[vtx], key=lambda f: f.raw.name)
            for idx, f in enumerate(strips):
                result[f.raw.name] = (edge, idx % n_strips)
    return result


def place_fixture(
    mf: MappedFixture, cfg: CubeConfig, corners: list[Corner] | None = None, beam: tuple | None = None
) -> Placement:
    """Resolve one addressable fixture to per-pixel positions + normals + identity.

    ``beam`` (edge, strip_index) places a structural beam/column strip on one of
    its per-face strips; pass it from :func:`assign_beam_strips`.
    """
    corners = corners or build_corners()

    if beam is not None:
        edge, idx = beam
        segs = _beam_face_strips(edge, cfg)
        p0, p1, normal = segs[min(idx, len(segs) - 1)]
        k = mf.raw.led_count
        pts, _ = _sample(p0, p1, k, mf.assoc.reverse)
        nrm = np.tile(normal.astype(np.float32), (k, 1))
        return Placement(pts, nrm, GROUP_EDGE, int(edge.index))
    vtx = mf.raw.vertex
    # Vertex -> corner: prefer the association's resolved corner id; else the
    # vertex table fallback (vertex 1..8 -> corner 0..7).
    cid = mf.assoc.element_id if (mf.assoc.kind == "corner" and mf.assoc.element_id is not None) else None
    if cid is None and vtx is not None:
        cid = (vtx - 1) % 8
    corner = corners[cid if cid is not None else 0]

    if mf.raw.section.startswith("corner"):
        return _place_corner(mf, corner, cfg)
    if mf.raw.section.startswith("vertical"):
        return _place_accent(mf, corner, cfg)
    # Unknown placeable section: cluster the LEDs at the vertex (visible, inert).
    k = mf.raw.led_count
    p = np.array(corner.signs, dtype=np.float64) * cfg.half
    pts = np.tile(p.astype(np.float32), (k, 1))
    nrm = np.tile((p / max(np.linalg.norm(p), 1e-9)).astype(np.float32), (k, 1))
    return Placement(pts, nrm, GROUP_EDGE, 0)
