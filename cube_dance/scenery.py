"""Optional non-LED scenery to make the simulation feel real: a clay ground,
surrounding bushes (it's a bush doof), and rough speaker cabinets (one sub
front-centre, two mains in the same plane) with little blue marker LEDs at their
base. Geometry only -- rough shapes, not accurate models.

Solid scenery is returned as combined (positions, normals, colors) arrays so the
whole lot draws in one call. Marker LEDs are returned separately as additive
points.
"""

from __future__ import annotations

import math

import numpy as np

from .config import CubeConfig

# Unit box: 6 faces, each (normal, 4 CCW corner sign-tuples).
_BOX_FACES = [
    ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
    ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
    ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
    ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
    ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
]

CLAY = (0.34, 0.23, 0.15)
SPEAKER = (0.07, 0.07, 0.08)
MARKER_BLUE = (0.12, 0.45, 1.0)


def _box(center: np.ndarray, size: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    half = size / 2.0
    pos, nrm = [], []
    for normal, quad in _BOX_FACES:
        corners = [center + np.array(s) * half for s in quad]
        for a, b, c in ((0, 1, 2), (0, 2, 3)):
            pos.extend([corners[a], corners[b], corners[c]])
            nrm.extend([normal, normal, normal])
    return np.array(pos, dtype=np.float32), np.array(nrm, dtype=np.float32)


def _uv_sphere(center: np.ndarray, radius: float, rings: int = 5, sectors: int = 8):
    grid = []
    for i in range(rings + 1):
        lat = math.pi * i / rings
        for j in range(sectors + 1):
            lon = 2 * math.pi * j / sectors
            grid.append(
                np.array([math.sin(lat) * math.cos(lon), math.cos(lat), math.sin(lat) * math.sin(lon)])
            )

    def at(i, j):
        return grid[i * (sectors + 1) + j]

    pos, nrm = [], []
    for i in range(rings):
        for j in range(sectors):
            a, b, c, d = at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)
            for tri in ((a, b, c), (a, c, d)):
                for n in tri:
                    nrm.append(n)
                    pos.append(center + n * radius)
    return np.array(pos, dtype=np.float32), np.array(nrm, dtype=np.float32)


def _colored(pos: np.ndarray, nrm: np.ndarray, color) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    col = np.tile(np.array(color, dtype=np.float32), (pos.shape[0], 1))
    return pos, nrm, col


def build_ground(cfg: CubeConfig, extent: float = 8.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = -cfg.half - 0.005  # just below the base LEDs to avoid z-fighting
    p = [
        (-extent, y, -extent), (extent, y, -extent), (extent, y, extent),
        (-extent, y, -extent), (extent, y, extent), (-extent, y, extent),
    ]
    pos = np.array(p, dtype=np.float32)
    nrm = np.tile(np.array([0, 1, 0], dtype=np.float32), (6, 1))
    return _colored(pos, nrm, CLAY)


def _speaker_layout(cfg: CubeConfig):
    """Return list of (center, size) for the sub + two mains (same z-plane)."""
    h = cfg.half
    floor = -h
    front_z = h + 0.75
    sub_size = np.array([0.62, 0.62, 0.62])
    main_size = np.array([0.45, 1.15, 0.5])
    return [
        (np.array([0.0, floor + sub_size[1] / 2, front_z]), sub_size),
        (np.array([-(h + 0.55), floor + main_size[1] / 2, front_z]), main_size),
        (np.array([(h + 0.55), floor + main_size[1] / 2, front_z]), main_size),
    ]


def build_speakers(cfg: CubeConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    parts = [_box(c, s) for c, s in _speaker_layout(cfg)]
    pos = np.concatenate([p for p, _ in parts], axis=0)
    nrm = np.concatenate([n for _, n in parts], axis=0)
    return _colored(pos, nrm, SPEAKER)


def build_speaker_markers(cfg: CubeConfig) -> tuple[np.ndarray, np.ndarray]:
    """Little blue LEDs ~1 inch off the ground at each speaker's front base."""
    y = -cfg.half + 0.025
    pos, col = [], []
    for center, size in _speaker_layout(cfg):
        front_z = center[2] + size[2] / 2 + 0.02
        pos.append([center[0], y, front_z])  # one centred marker per speaker
        col.append(MARKER_BLUE)
    return np.array(pos, dtype=np.float32), np.array(col, dtype=np.float32)


def build_bushes(cfg: CubeConfig, count: int = 44, seed: int = 7):
    rng = np.random.default_rng(seed)
    floor = -cfg.half
    pos_all, nrm_all, col_all = [], [], []
    for _ in range(count):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(5.6, 6.7)  # a perimeter ring at the clearing's edge
        cx, cz = rad * math.cos(ang), rad * math.sin(ang)
        green = np.array([rng.uniform(0.04, 0.10), rng.uniform(0.16, 0.30), rng.uniform(0.05, 0.11)])
        for _ in range(rng.integers(2, 5)):
            r = rng.uniform(0.28, 0.55)
            off = rng.uniform(-0.35, 0.35, size=2)
            center = np.array([cx + off[0], floor + r * 0.7, cz + off[1]])
            p, n = _uv_sphere(center, r)
            pos_all.append(p)
            nrm_all.append(n)
            col_all.append(np.tile(green.astype(np.float32), (p.shape[0], 1)))
    pos = np.concatenate(pos_all, axis=0)
    nrm = np.concatenate(nrm_all, axis=0)
    col = np.concatenate(col_all, axis=0)
    return pos, nrm, col


def build_solids(cfg: CubeConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Combined (positions, normals, colors) for all enabled solid scenery."""
    parts: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    if cfg.show_floor:
        parts.append(build_ground(cfg))
    if cfg.show_speakers:
        parts.append(build_speakers(cfg))
    if cfg.show_bushes:
        parts.append(build_bushes(cfg))
    if not parts:
        empty = np.zeros((0, 3), dtype=np.float32)
        return empty, empty, empty
    pos = np.concatenate([p for p, _, _ in parts], axis=0)
    nrm = np.concatenate([n for _, n, _ in parts], axis=0)
    col = np.concatenate([c for _, _, c in parts], axis=0)
    return pos, nrm, col
