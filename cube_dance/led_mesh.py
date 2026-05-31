"""Emissive LED-strip geometry: one thin tube per LED run.

Replaces point-sprite LEDs (whose single per-sprite depth made beams pop in/out
behind the truss tubes, view-dependently). A solid tube has proper per-fragment
depth, so it occludes and is occluded correctly with no popping, and being solid
emissive geometry its brightness doesn't depend on the view angle or sprite
overlap. Each tube carries a per-vertex texture coordinate into the LED color
buffer (uploaded as a 1-D texture), so colour varies per pixel along the run.
"""

from __future__ import annotations

import math

import numpy as np

from .led_topology import CubeModel


def _cylinder_param(p0, p1, radius, sides):
    """Tube from p0->p1. Returns (pos (V,3), nrm (V,3), t (V,)), t=0 at p0, 1 at p1."""
    p0 = np.asarray(p0, np.float64)
    p1 = np.asarray(p1, np.float64)
    axis = p1 - p0
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return None
    d = axis / length
    up = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, up); u /= np.linalg.norm(u)
    v = np.cross(d, u)
    ring = np.array([math.cos(a) * u + math.sin(a) * v for a in np.linspace(0, 2 * np.pi, sides, endpoint=False)])
    bottom = p0[None, :] + radius * ring
    top = p1[None, :] + radius * ring
    pos, nrm, t = [], [], []
    for i in range(sides):
        j = (i + 1) % sides
        verts = [(bottom[i], ring[i], 0.0), (bottom[j], ring[j], 0.0), (top[j], ring[j], 1.0),
                 (bottom[i], ring[i], 0.0), (top[j], ring[j], 1.0), (top[i], ring[i], 1.0)]
        for p, nm, tt in verts:
            pos.append(p); nrm.append(nm); t.append(tt)
    return np.array(pos, np.float32), np.array(nrm, np.float32), np.array(t, np.float32)


def build_led_strips(
    model: CubeModel, radius: float = 0.011, offset: float = 0.032, sides: int = 6
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (positions (V,3), normals (V,3), texcoord (V,)) for all LED runs.

    ``texcoord`` indexes the LED color buffer (a 1-D texture of width N) so the
    strip is coloured per pixel along its length.
    """
    n = model.n
    pos_all, nrm_all, uv_all = [], [], []
    for start, length in model.run_spans:
        if length < 2:
            continue
        a = model.positions[start] + model.normal[start] * offset
        b = model.positions[start + length - 1] + model.normal[start + length - 1] * offset
        built = _cylinder_param(a, b, radius, sides)
        if built is None:
            continue
        p, nm, t = built
        idx = start + t * (length - 1)  # LED index along the run
        pos_all.append(p)
        nrm_all.append(nm)
        uv_all.append((idx + 0.5) / n)  # texel-centre coordinate in [0,1]
    pos = np.concatenate(pos_all, axis=0)
    nrm = np.concatenate(nrm_all, axis=0)
    uv = np.concatenate(uv_all, axis=0).astype(np.float32)
    return pos, nrm, uv
