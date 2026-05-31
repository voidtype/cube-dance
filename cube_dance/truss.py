"""F34-style truss geometry as low-poly tubes (cylinders).

Built from the same edge/corner geometry the LEDs use, so the LED chord rows sit
on the chord tubes. Per edge: 4 chord tubes over the lit run + diagonal lacing
(the triangles) on the two outward faces. Per corner: the 12 corner-cube frame
tubes + X bracing. Returns one combined (positions, normals) mesh for the metal
shader; nothing here is LED-coloured.
"""

from __future__ import annotations

import math

import numpy as np

from .config import CubeConfig
from .geometry import _other_axes, build_corners, build_edges, corner_cube_edges, corner_x_faces


def cylinder(p0, p1, radius: float, sides: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """A low-poly tube between p0 and p1 → (positions (T,3), normals (T,3))."""
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    axis = p1 - p0
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)
    d = axis / length
    up = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, up); u /= np.linalg.norm(u)
    v = np.cross(d, u)
    ang = np.linspace(0.0, 2 * np.pi, sides, endpoint=False)
    ring = np.array([math.cos(a) * u + math.sin(a) * v for a in ang])  # (sides,3) unit radial
    bottom = p0[None, :] + radius * ring
    top = p1[None, :] + radius * ring

    pos, nrm = [], []
    for i in range(sides):
        j = (i + 1) % sides
        quad = [(bottom[i], ring[i]), (bottom[j], ring[j]), (top[j], ring[j]), (top[i], ring[i])]
        for a, b, c in ((0, 1, 2), (0, 2, 3)):
            for k in (a, b, c):
                pos.append(quad[k][0])
                nrm.append(quad[k][1])
    return np.array(pos, np.float32), np.array(nrm, np.float32)


def build_truss(
    cfg: CubeConfig,
    chord_radius: float = 0.022,
    lace_radius: float = 0.013,
    lacing: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Combined truss mesh (positions (T,3), normals (T,3))."""
    eh, h = cfg.edge_half, cfg.half
    pos_all: list[np.ndarray] = []
    nrm_all: list[np.ndarray] = []

    def add(p0, p1, r):
        p, n = cylinder(p0, p1, r)
        if len(p):
            pos_all.append(p)
            nrm_all.append(n)

    for edge in build_edges():
        axis = edge.axis
        d0, d1 = _other_axes(axis)
        s0, s1 = edge.fixed

        def at(c0, c1, t):
            p = np.zeros(3)
            p[axis] = t
            p[d0] = c0
            p[d1] = c1
            return p

        # 4 chords over the lit run.
        chords = [(s0 * eh, s1 * eh), (s0 * eh, s1 * h), (s0 * h, s1 * eh), (s0 * h, s1 * h)]
        for c0, c1 in chords:
            add(at(c0, c1, -eh), at(c0, c1, eh), chord_radius)

        # Diagonal lacing (triangles) on the two outward faces (+d0 and +d1).
        if lacing:
            nseg = max(2, int(round((2 * eh) / 0.33)))
            ts = np.linspace(-eh, eh, nseg + 1)
            faces = [
                ((s0 * h, s1 * eh), (s0 * h, s1 * h)),  # +d0 face
                ((s0 * eh, s1 * h), (s0 * h, s1 * h)),  # +d1 face
            ]
            for ca, cb in faces:
                for k in range(nseg):
                    a, b = (ca, cb) if k % 2 == 0 else (cb, ca)
                    add(at(a[0], a[1], ts[k]), at(b[0], b[1], ts[k + 1]), lace_radius)

    for corner in build_corners():
        for a, b in corner_cube_edges(corner, cfg):
            add(a, b, chord_radius * 0.8)
        for a, b, _normal in corner_x_faces(corner, cfg):
            add(a, b, lace_radius)

    pos = np.concatenate(pos_all, axis=0)
    nrm = np.concatenate(nrm_all, axis=0)
    return pos, nrm
