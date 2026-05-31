"""Dense abstract LED topology over the cube geometry.

Builds the flat, index-aligned arrays that make up :class:`CubeModel`. The pixel
address is the array index. Addressing is deterministic: all edge pixels first
(edges 0..11 in canonical order, each with its lit chord rows), then all corner
pixels (corners 0..7: corner-cube edges, then X panels).

These are *abstract* LED pixels (a dense visual representation), not models of
individual physical LEDs -- downstream mapping software handles real pixels.
"""

from __future__ import annotations

import numpy as np

from .config import CubeConfig
from .geometry import (
    _other_axes,
    build_corners,
    build_edges,
    corner_cube_edges,
    corner_x_faces,
    edge_chord_rows,
    structure_line_vertices,
)

GROUP_EDGE = np.uint8(0)
GROUP_CORNER = np.uint8(1)


def _edge_chord_normal(edge, cfg: CubeConfig, p0: np.ndarray) -> np.ndarray:
    """Outward unit normal of an edge chord (from the beam centre line)."""
    d0, d1 = _other_axes(edge.axis)
    mid = (cfg.edge_half + cfg.half) / 2.0
    n = np.zeros(3)
    n[d0] = p0[d0] - edge.fixed[0] * mid
    n[d1] = p0[d1] - edge.fixed[1] * mid
    norm = np.linalg.norm(n)
    return n / norm if norm > 1e-9 else n


def _samples(p0: np.ndarray, p1: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """``n`` evenly spaced points from ``p0`` to ``p1`` inclusive.

    Returns ``(points (n,3), t (n,))`` where ``t`` is the normalised parameter.
    """
    t = np.linspace(0.0, 1.0, n)
    return p0[None, :] + t[:, None] * (p1 - p0)[None, :], t


class CubeModel:
    """The cube's LEDs as index-aligned arrays plus the shared color buffer.

    Attributes (all length ``N``, indexed by pixel address):
        positions:  (N, 3) float32 metres, centred, +Y up.
        group:      (N,)   uint8  -- GROUP_EDGE or GROUP_CORNER.
        element_id: (N,)   int32  -- edge id 0..11 or corner id 0..7.
        param:      (N,)   float32 -- normalised position along the segment.
        colors:     (N, 3) float32 in [0, 1] -- the mutable write contract.
    """

    def __init__(self, cfg: CubeConfig) -> None:
        self.cfg = cfg
        positions: list[np.ndarray] = []
        group: list[np.ndarray] = []
        element_id: list[np.ndarray] = []
        param: list[np.ndarray] = []
        normals: list[np.ndarray] = []

        def add(p0, p1, n, grp, eid, *, normal_const=None, center=None):
            pts, t = _samples(p0, p1, n)
            positions.append(pts)
            group.append(np.full(n, grp))
            element_id.append(np.full(n, eid, dtype=np.int32))
            param.append(t.astype(np.float32))
            if normal_const is not None:
                normals.append(np.tile(normal_const.astype(np.float32), (n, 1)))
            else:  # outward from a centre point (corners)
                d = pts - center
                norm = np.linalg.norm(d, axis=1, keepdims=True)
                normals.append((d / np.where(norm > 1e-9, norm, 1.0)).astype(np.float32))

        # --- Edges first (each edge: one or more lit chord rows) ---
        n_edge = cfg.edge_pixel_count()
        for edge in build_edges():
            for p0, p1 in edge_chord_rows(edge, cfg):
                add(p0, p1, n_edge, GROUP_EDGE, edge.index, normal_const=_edge_chord_normal(edge, cfg, p0))

        # --- Corners: cube-edge outline (optional) + X panels ---
        n_cedge = cfg.corner_edge_pixel_count()
        n_diag = cfg.corner_diagonal_pixel_count()
        mid = (cfg.edge_half + cfg.half) / 2.0
        for corner in build_corners():
            center = np.array(corner.signs, dtype=np.float64) * mid  # corner-cube centre
            if cfg.corner_edges:
                for p0, p1 in corner_cube_edges(corner, cfg):
                    add(p0, p1, n_cedge, GROUP_CORNER, corner.index, center=center)
            for p0, p1, face_normal in corner_x_faces(corner, cfg):
                # Lift X LEDs straight out of their face (coplanar -> no mutual occlusion).
                add(p0, p1, n_diag, GROUP_CORNER, corner.index, normal_const=face_normal)

        self.positions = np.concatenate(positions, axis=0).astype(np.float32)
        self.group = np.concatenate(group).astype(np.uint8)
        self.element_id = np.concatenate(element_id).astype(np.int32)
        self.param = np.concatenate(param).astype(np.float32)
        self.normal = np.concatenate(normals, axis=0).astype(np.float32)
        self.colors = np.zeros_like(self.positions)  # (N, 3) float32, LEDs off

        # --- Precomputed region index lists for O(1) vectorised writes ---
        self.edge_mask = self.group == GROUP_EDGE
        self.corner_mask = self.group == GROUP_CORNER
        self.edge_indices: dict[int, np.ndarray] = {
            e.index: np.where(self.edge_mask & (self.element_id == e.index))[0]
            for e in build_edges()
        }
        self.corner_indices: dict[int, np.ndarray] = {
            c.index: np.where(self.corner_mask & (self.element_id == c.index))[0]
            for c in build_corners()
        }

    @property
    def n(self) -> int:
        return self.positions.shape[0]

    def reset_colors(self) -> None:
        self.colors[:] = 0.0

    def structure_lines(self) -> np.ndarray:
        return structure_line_vertices(self.cfg)


def build_model(cfg: CubeConfig | None = None) -> CubeModel:
    return CubeModel(cfg or CubeConfig())
