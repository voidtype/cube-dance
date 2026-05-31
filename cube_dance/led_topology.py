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
    build_corners,
    build_edges,
    corner_cube_edges,
    corner_x_faces,
    edge_chord_rows,
    structure_line_vertices,
)

GROUP_EDGE = np.uint8(0)
GROUP_CORNER = np.uint8(1)


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

        def add(p0, p1, n, grp, eid):
            pts, t = _samples(p0, p1, n)
            positions.append(pts)
            group.append(np.full(n, grp))
            element_id.append(np.full(n, eid, dtype=np.int32))
            param.append(t.astype(np.float32))

        # --- Edges first (each edge: one or more lit chord rows) ---
        n_edge = cfg.edge_pixel_count()
        for edge in build_edges():
            for p0, p1 in edge_chord_rows(edge, cfg):
                add(p0, p1, n_edge, GROUP_EDGE, edge.index)

        # --- Corners: cube-edge outline (optional) + X panels ---
        n_cedge = cfg.corner_edge_pixel_count()
        n_diag = cfg.corner_diagonal_pixel_count()
        for corner in build_corners():
            if cfg.corner_edges:
                for p0, p1 in corner_cube_edges(corner, cfg):
                    add(p0, p1, n_cedge, GROUP_CORNER, corner.index)
            for p0, p1 in corner_x_faces(corner, cfg):
                add(p0, p1, n_diag, GROUP_CORNER, corner.index)

        self.positions = np.concatenate(positions, axis=0).astype(np.float32)
        self.group = np.concatenate(group).astype(np.uint8)
        self.element_id = np.concatenate(element_id).astype(np.int32)
        self.param = np.concatenate(param).astype(np.float32)
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
