"""The real cube as a drop-in CubeModel (Phase 3).

:class:`HardwareCubeModel` exposes the exact attribute contract that effects and
the engine read from :class:`cube_dance.led_topology.CubeModel` — ``positions``,
``normal``, ``element_id``, ``param``, ``group``, ``colors``, the edge/corner
masks + index dicts, ``region_indices``, ``run_spans``, ``cfg`` — but built from
the *real* fixture inventory instead of the idealised dense model.

Two things make it correct as a substitute:

* **Geometry** comes from placing each fixture onto the physical cube
  (:mod:`cube_dance.hardware.placement`), so distance/normal/height/angle effects
  read meaningful 3-D values.
* **Pixel order** is ``mapping.output_order()`` — the same canonical order the
  :class:`~cube_dance.hardware.artnet.ArtnetLayout` packs — so colour-buffer row
  ``i`` drives the same physical LED the ArtNet sink sends row ``i`` to. The model
  and the sink are aligned by construction.

Build it, hand it to a :class:`~cube_dance.visuals.engine.VisualEngine`, run any
preset, then pack ``model.colors`` with the sink — no effect code changes.
"""

from __future__ import annotations

import numpy as np

from ..config import CubeConfig
from ..geometry import build_corners, build_edges
from ..led_topology import GROUP_CORNER, GROUP_EDGE
from .mapping import Mapping, build_mapping
from .placement import place_fixture


class HardwareCubeModel:
    """A real-fixture cube model with the CubeModel interface effects expect."""

    def __init__(self, mapping: Mapping, cfg: CubeConfig | None = None) -> None:
        self.cfg = cfg or CubeConfig()
        self.mapping = mapping
        corners = build_corners()

        fixtures = mapping.output_order()
        positions: list[np.ndarray] = []
        normals: list[np.ndarray] = []
        group: list[np.ndarray] = []
        element_id: list[np.ndarray] = []
        param: list[np.ndarray] = []
        spans: list[tuple[int, int]] = []
        self.fixture_slices: dict[str, tuple[int, int]] = {}

        total = 0
        for mf in fixtures:
            pl = place_fixture(mf, self.cfg, corners)
            k = pl.positions.shape[0]
            positions.append(pl.positions)
            normals.append(pl.normals)
            group.append(np.full(k, pl.group, dtype=np.uint8))
            element_id.append(np.full(k, pl.element_id, dtype=np.int32))
            param.append(np.linspace(0.0, 1.0, k, dtype=np.float32))
            spans.append((total, k))
            self.fixture_slices[mf.raw.name] = (total, k)
            total += k

        if positions:
            self.positions = np.concatenate(positions, axis=0).astype(np.float32)
            self.normal = np.concatenate(normals, axis=0).astype(np.float32)
            self.group = np.concatenate(group).astype(np.uint8)
            self.element_id = np.concatenate(element_id).astype(np.int32)
            self.param = np.concatenate(param).astype(np.float32)
        else:  # empty mapping (no addressable fixtures)
            self.positions = np.zeros((0, 3), np.float32)
            self.normal = np.zeros((0, 3), np.float32)
            self.group = np.zeros((0,), np.uint8)
            self.element_id = np.zeros((0,), np.int32)
            self.param = np.zeros((0,), np.float32)

        self.run_spans = spans
        self.colors = np.zeros_like(self.positions)

        # Region masks + per-element index lists (same shapes/keys as CubeModel).
        self.edge_mask = self.group == GROUP_EDGE
        self.corner_mask = self.group == GROUP_CORNER
        self.edge_indices = {
            e.index: np.where(self.edge_mask & (self.element_id == e.index))[0]
            for e in build_edges()
        }
        self.corner_indices = {
            c.index: np.where(self.corner_mask & (self.element_id == c.index))[0]
            for c in build_corners()
        }
        x, y, z = self.positions[:, 0], self.positions[:, 1], self.positions[:, 2]
        self.region_indices = {
            "left": np.where(x < 0)[0], "right": np.where(x >= 0)[0],
            "bottom": np.where(y < 0)[0], "top": np.where(y >= 0)[0],
            "back": np.where(z < 0)[0], "front": np.where(z >= 0)[0],
        }

    @property
    def n(self) -> int:
        return self.positions.shape[0]

    def reset_colors(self) -> None:
        self.colors[:] = 0.0

    def structure_lines(self) -> np.ndarray:
        from ..geometry import structure_line_vertices
        return structure_line_vertices(self.cfg)


def build_hardware_model(
    json_path: str | None = None, config_path: str | None = None, cfg: CubeConfig | None = None
) -> HardwareCubeModel:
    """Convenience: load the default mapping and build the hardware model."""
    return HardwareCubeModel(build_mapping(json_path, config_path), cfg)
