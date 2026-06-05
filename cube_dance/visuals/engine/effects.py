"""20 new 3-D effect elements (see docs/effect-ideas.md).

Each is an Element that writes a *continuous* (non-event-gated) contribution, so
its preset reads even without transients. Families: simulation, fractal/noise,
geometric/implicit, structure-aware (edges/corners/normals), and physical/waves.
"""

from __future__ import annotations

import math

import numpy as np

from ...patterns import hsv_to_rgb
from .context import Context, EnvFollower
from .element import Element

_RNG = np.random.default_rng()


def _u01(model) -> np.ndarray:
    """LED positions normalised to [0,1]^3."""
    return np.clip((model.positions + model.cfg.half) / model.cfg.side_m, 0.0, 1.0).astype(np.float32)


def _pn(model) -> np.ndarray:
    """LED positions normalised to roughly [-1,1]^3 (÷half)."""
    return (model.positions / model.cfg.half).astype(np.float32)


def _edge_sequence(model):
    """Edge-LED indices ordered edge-by-edge then along each edge (a path)."""
    idx = np.where(model.edge_mask)[0]
    order = np.lexsort((model.param[idx], model.element_id[idx]))
    return idx[order]


# --- A. Simulation / algorithmic -------------------------------------------

class GameOfLife3D(Element):
    """A 3-D life-like cellular automaton on a coarse voxel grid; kicks re-seed."""

    blend = "add"

    def __init__(self, model, g: int = 14, hue: float = 0.33, sat: float = 0.8, step_hz: float = 6.0):
        idx = np.clip((_u01(model) * g).astype(int), 0, g - 1)
        self.vid = (idx[:, 0] * g + idx[:, 1]) * g + idx[:, 2]
        self.g, self.hue, self.sat, self.step_hz = g, hue, sat, step_hz
        self.grid = _RNG.random((g, g, g)) < 0.2
        self.field = np.zeros(model.n, np.float32)
        self._acc = 0.0

    def _step(self):
        g = self.grid
        nb = np.zeros(g.shape, np.int8)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx or dy or dz:
                        nb += np.roll(np.roll(np.roll(g, dx, 0), dy, 1), dz, 2)
        self.grid = ((~g) & (nb == 6)) | (g & ((nb >= 5) & (nb <= 7)))
        if self.grid.sum() < self.grid.size * 0.02:  # don't die out
            self.grid |= _RNG.random(self.grid.shape) < 0.08

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._acc += ctx.dt * self.step_hz * (0.4 + ctx.energy)
        if self._acc >= 1.0:
            self._acc = 0.0
            self._step()
        if ctx.events("kick"):
            self.grid |= _RNG.random(self.grid.shape) < 0.12
        target = self.grid.reshape(-1).astype(np.float32)[self.vid]
        self.field += (target - self.field) * min(1.0, ctx.dt * 8.0)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          self.field * (0.45 + 0.55 * ctx.energy))


class ReactionDiffusion(Element):
    """Gray–Scott reaction–diffusion on a coarse grid → organic morphing patterns."""

    blend = "add"

    def __init__(self, model, g: int = 20, hue: float = 0.45, sat: float = 0.85,
                 feed: float = 0.037, kill: float = 0.062):
        self.g = g
        self.A = np.ones((g, g, g), np.float32)
        self.B = np.zeros((g, g, g), np.float32)
        self._seed()
        idx = np.clip((_u01(model) * g).astype(int), 0, g - 1)
        self.vid = (idx[:, 0] * g + idx[:, 1]) * g + idx[:, 2]
        self.feed, self.kill, self.hue, self.sat = feed, kill, hue, sat

    def _seed(self):
        c = self.g // 2
        self.B[c - 2:c + 3, c - 2:c + 3, c - 2:c + 3] = 1.0

    @staticmethod
    def _lap(X):
        return (-6.0 * X + np.roll(X, 1, 0) + np.roll(X, -1, 0) + np.roll(X, 1, 1)
                + np.roll(X, -1, 1) + np.roll(X, 1, 2) + np.roll(X, -1, 2))

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        for _ in range(2):
            A, B = self.A, self.B
            ab2 = A * B * B
            self.A = np.clip(A + 0.19 * self._lap(A) - ab2 + self.feed * (1 - A), 0, 1)
            self.B = np.clip(B + 0.09 * self._lap(B) + ab2 - (self.kill + self.feed) * B, 0, 1)
        if self.B.sum() < 1.0:
            self._seed()
        val = np.clip(self.B.reshape(-1)[self.vid] * 2.6, 0, 1).astype(np.float32)
        out += hsv_to_rgb((self.hue + 0.2 * val + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          val * (0.5 + 0.5 * ctx.energy))


class Boids(Element):
    """A flock of boids fly in 3-D; LEDs glow near the nearest boid (murmuration)."""

    blend = "add"

    def __init__(self, model, n: int = 36, hue: float = 0.55, sat: float = 0.85, width: float = 0.16):
        self.pos = ((_RNG.random((n, 3)) * 2 - 1) * 0.8).astype(np.float32)
        self.vel = ((_RNG.random((n, 3)) * 2 - 1) * 0.3).astype(np.float32)
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        dt = min(ctx.dt, 0.05)
        pos, vel = self.pos, self.vel
        vel += (pos.mean(0) - pos) * 0.6 * dt  # cohesion
        for i in range(len(pos)):  # separation
            d = pos - pos[i]
            close = (d * d).sum(1) < 0.09
            vel[i] -= d[close].sum(0) * 0.4 * dt
        if ctx.events("kick"):
            vel += (_RNG.random((len(pos), 3)) * 2 - 1) * 0.6
        spd = 0.4 + 0.9 * ctx.energy
        vel *= (spd / (np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6))
        pos += vel * dt
        over = np.abs(pos) > 1.0
        vel[over] *= -1.0
        self.pos, self.vel = np.clip(pos, -1, 1), vel
        dx = self.P[:, 0, None] - pos[:, 0][None, :]
        dy = self.P[:, 1, None] - pos[:, 1][None, :]
        dz = self.P[:, 2, None] - pos[:, 2][None, :]
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (self.width ** 2)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class DLA(Element):
    """Diffusion-limited aggregation: a dendritic crystal slowly grows in 3-D."""

    blend = "add"

    def __init__(self, model, g: int = 18, hue: float = 0.6, sat: float = 0.85):
        self.g = g
        self.occ = _RNG.random((g, g, g)) < 0.01
        self.occ[g // 2, g // 2, g // 2] = True
        idx = np.clip((_u01(model) * g).astype(int), 0, g - 1)
        self.vid = (idx[:, 0] * g + idx[:, 1]) * g + idx[:, 2]
        self.hue, self.sat = hue, sat
        self.field = np.zeros(model.n, np.float32)

    def _grow(self, walkers: int):
        g, occ = self.g, self.occ
        for _ in range(walkers):
            p = _RNG.integers(0, g, 3)
            for _ in range(40):
                p = (p + _RNG.integers(-1, 2, 3)) % g
                x, y, z = int(p[0]), int(p[1]), int(p[2])
                if (occ[(x + 1) % g, y, z] or occ[x - 1, y, z] or occ[x, (y + 1) % g, z]
                        or occ[x, y - 1, z] or occ[x, y, (z + 1) % g] or occ[x, y, z - 1]):
                    occ[x, y, z] = True
                    break

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._grow(2 + int(6 * ctx.energy))
        target = self.occ.reshape(-1).astype(np.float32)[self.vid]
        self.field += (target - self.field) * min(1.0, ctx.dt * 5.0)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          self.field * (0.5 + 0.5 * ctx.energy))


# --- B. Fractal / noise -----------------------------------------------------

class FbmCloud(Element):
    """Layered (fractal) noise drifting through the cube — a turbulent colour cloud."""

    blend = "add"

    def __init__(self, model, hue: float = 0.55, sat: float = 0.8, base: float = 0.55):
        self.P = _pn(model)
        self.hue, self.sat, self.base = hue, sat, base

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t, P = ctx.t, self.P
        v = np.zeros(len(P), np.float32)
        amp, freq = 1.0, 1.0 * (0.6 + ctx.size)
        for _ in range(4):
            v += amp * (np.sin(P[:, 0] * freq + t * 0.3) * np.sin(P[:, 1] * freq * 1.3 - t * 0.2)
                        * np.sin(P[:, 2] * freq * 0.8 + t * 0.25))
            amp *= 0.5
            freq *= 2.0
        v /= 1.875
        val = np.clip(self.base * (0.5 + 0.5 * v) * (0.55 + 0.6 * ctx.energy), 0, 1).astype(np.float32)
        out += hsv_to_rgb((self.hue + 0.2 * v + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


class MengerSponge(Element):
    """Light LEDs inside a (slowly drifting) Menger sponge — a cube fractal in the cube."""

    blend = "add"

    def __init__(self, model, hue: float = 0.08, sat: float = 0.9, levels: int = 3):
        self.u = _u01(model)
        self.hue, self.sat, self.levels = hue, sat, levels

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        cur = (self.u + np.array([t * 0.03, t * 0.01, t * 0.02], np.float32)) % 1.0
        inside = np.ones(len(cur), bool)
        for _ in range(self.levels):
            cur = cur * 3.0
            d = np.floor(cur).astype(int) % 3
            cur = cur - np.floor(cur)
            inside &= (d == 1).sum(axis=1) < 2
        val = inside.astype(np.float32) * (0.45 + 0.55 * ctx.energy)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


class Mandelbulb(Element):
    """Escape-time of the Mandelbulb sampled on the cube shell, slowly rotating."""

    blend = "add"

    def __init__(self, model, power: float = 8.0, hue: float = 0.6, sat: float = 0.9, iters: int = 6):
        self.c0 = (_pn(model) * 1.15).astype(np.float32)
        self.power, self.hue, self.sat, self.iters = power, hue, sat, iters

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        a = ctx.t * 0.2
        ca, sa = math.cos(a), math.sin(a)
        cx = self.c0[:, 0] * ca + self.c0[:, 2] * sa
        cz = -self.c0[:, 0] * sa + self.c0[:, 2] * ca
        cy = self.c0[:, 1]
        zx, zy, zz = cx.copy(), cy.copy(), cz.copy()
        esc = np.zeros(len(cx), np.float32)
        with np.errstate(over="ignore", invalid="ignore"):
            for i in range(self.iters):
                r = np.sqrt(zx * zx + zy * zy + zz * zz) + 1e-9
                theta = np.arccos(np.clip(zz / r, -1, 1)) * self.power
                phi = np.arctan2(zy, zx) * self.power
                rp = np.minimum(r, 1.8) ** self.power  # clamp to avoid overflow (escaped anyway)
                st = np.sin(theta)
                zx = rp * st * np.cos(phi) + cx
                zy = rp * st * np.sin(phi) + cy
                zz = rp * np.cos(theta) + cz
                newly = (esc == 0) & (zx * zx + zy * zy + zz * zz > 4.0)
                esc[newly] = i + 1
        val = np.where(esc == 0, 0.0, 1.0 - esc / self.iters).astype(np.float32)  # near-surface glow
        out += hsv_to_rgb((self.hue + 0.5 * val + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          val * (0.5 + 0.5 * ctx.energy))


# --- C. Geometric / implicit ------------------------------------------------

class SlicePlane(Element):
    """A flat plane sweeps and rotates through the cube; LEDs near it light (a cross-section)."""

    blend = "add"

    def __init__(self, model, hue: float = 0.5, sat: float = 0.95, width: float = 0.1):
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        a, b = t * 0.3, t * 0.17
        n = np.array([math.cos(a) * math.cos(b), math.sin(b), math.sin(a) * math.cos(b)], np.float32)
        d = np.abs(self.P @ n - 0.7 * math.sin(t * 0.5))
        band = np.clip(1.0 - d / (self.width * (0.6 + ctx.size)), 0, 1).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.4 * ctx.energy))


class SphereShell(Element):
    """A sphere shell whose radius breathes with the bass — the cube inhales/exhales."""

    blend = "add"

    def __init__(self, model, hue: float = 0.0, sat: float = 0.9, width: float = 0.1):
        rho = np.sqrt((_pn(model) ** 2).sum(1))
        self.rho = (rho / (float(rho.max()) or 1.0)).astype(np.float32)  # 0..1 (corners = 1)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        bass = float(getattr(ctx.features, "bass", 0.0) or 0.0)
        r = 0.82 + 0.15 * bass + 0.14 * math.sin(ctx.t * 0.6)  # sweeps the edge->corner band
        band = np.clip(1.0 - np.abs(self.rho - r) / self.width, 0, 1).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class TorusKnot(Element):
    """A parametric (p,q) torus-knot curve threads the cube; LEDs near it light."""

    blend = "add"

    def __init__(self, model, p: int = 2, q: int = 3, R: float = 1.0, r: float = 0.45,
                 hue: float = 0.4, sat: float = 0.9, width: float = 0.18, samples: int = 200):
        self.P = _pn(model)
        self.p, self.q, self.R, self.r = p, q, R, r
        self.hue, self.sat, self.width = hue, sat, width
        self.s = np.linspace(0.0, 2 * np.pi, samples, dtype=np.float32)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        s = self.s + ctx.t * 0.3
        rr = self.R + self.r * np.cos(self.q * s)
        px, py, pz = rr * np.cos(self.p * s), rr * np.sin(self.p * s), self.r * np.sin(self.q * s)
        dx = self.P[:, 0, None] - px[None, :]
        dy = self.P[:, 1, None] - py[None, :]
        dz = self.P[:, 2, None] - pz[None, :]
        w = self.width * (0.7 + ctx.size)
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (w * w)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class PlatonicSolid(Element):
    """A wireframe icosahedron of light rotating inside the cube (proximity to its edges)."""

    blend = "add"
    _EDGES = [(0, 1), (0, 5), (0, 7), (0, 10), (0, 11), (1, 5), (1, 7), (1, 8), (1, 9), (2, 3),
              (2, 4), (2, 6), (2, 10), (2, 11), (3, 4), (3, 6), (3, 8), (3, 9), (4, 5), (4, 9),
              (4, 11), (5, 9), (5, 11), (6, 7), (6, 8), (6, 10), (7, 8), (7, 10), (8, 9), (10, 11)]

    def __init__(self, model, scale: float = 1.5, hue: float = 0.33, sat: float = 0.9, width: float = 0.24):
        phi = (1 + 5 ** 0.5) / 2
        v = np.array([(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi),
                      (0, -1, -phi), (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)], float)
        v /= np.linalg.norm(v[0])
        pts = [v[a] * (1 - f) + v[b] * f for a, b in self._EDGES for f in np.linspace(0, 1, 8)]
        self.pts0 = (np.array(pts, np.float32) * scale)
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        a = ctx.t * 0.4 * (0.5 + ctx.energy)
        ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(a * 0.6), math.sin(a * 0.6)
        p = self.pts0
        x = p[:, 0] * ca + p[:, 2] * sa
        z = -p[:, 0] * sa + p[:, 2] * ca
        y = p[:, 1] * cb - z * sb
        z = p[:, 1] * sb + z * cb
        dx = self.P[:, 0, None] - x[None, :]
        dy = self.P[:, 1, None] - y[None, :]
        dz = self.P[:, 2, None] - z[None, :]
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (self.width ** 2)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


# --- D. Structure-aware (edges, corners, normals) ---------------------------

class EdgeSnake(Element):
    """A light that walks the cube's edge graph, turning onto a connected edge at
    each corner (a Tron light-cycle on the truss) and leaving a fading trail.

    Uses the real adjacency: each edge's two ends map to one of the 8 cube corners
    (by sign of position), and three edges meet at every corner — so when the head
    reaches a corner it picks one of the *other* edges there and carries on. The
    corner's own LED cluster lights as it passes, so it flows through the joint.
    """

    blend = "add"
    _rng = np.random.default_rng()

    @staticmethod
    def _corner(pos) -> int:
        return int(pos[0] > 0) * 4 + int(pos[1] > 0) * 2 + int(pos[2] > 0)

    def __init__(self, model, hue: float = 0.33, sat: float = 0.95, head: float = 0.13,
                 speed: float = 1.1, release: float = 0.85):
        eidx = np.where(model.edge_mask)[0]
        eid = model.element_id[eidx]
        self.edges = []  # per edge: led idx (sorted by param), params, corner at each end
        for e in np.unique(eid):
            sel = eidx[eid == e]
            order = np.argsort(model.param[sel])
            sel = sel[order]
            par = model.param[sel].astype(np.float32)
            c0 = self._corner(model.positions[sel[0]])
            c1 = self._corner(model.positions[sel[-1]])
            self.edges.append({"idx": sel, "par": par, "c": (c0, c1)})
        # corner -> list of (edge, end) meeting there
        self.by_corner: dict[int, list] = {}
        for ei, ed in enumerate(self.edges):
            for end in (0, 1):
                self.by_corner.setdefault(ed["c"][end], []).append((ei, end))
        # corner cluster LEDs grouped by corner (to bridge the joint as the snake passes)
        ci = np.where(model.corner_mask)[0]
        cids = np.array([self._corner(p) for p in model.positions[ci]])
        self.corner_leds = {c: ci[cids == c] for c in range(8)}
        self.hue, self.sat, self.head, self.speed, self.release = hue, sat, head, speed, release
        self.bright = np.zeros(model.n, np.float32)
        self.cur, self.hp, self.dir = 0, 0.0, 1.0

    def _turn(self, end: int) -> None:
        corner = self.edges[self.cur]["c"][end]
        self.bright[self.corner_leds.get(corner, [])] = 1.0  # flow through the joint
        nbrs = [x for x in self.by_corner.get(corner, []) if x != (self.cur, end)]
        if not nbrs:
            self.dir = -self.dir
            return
        ej, endj = nbrs[int(self._rng.integers(len(nbrs)))]
        self.cur = ej
        self.hp, self.dir = (0.0, 1.0) if endj == 0 else (1.0, -1.0)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        if ctx.dt > 0:
            self.bright *= math.exp(-ctx.dt / self.release)
        self.hp += self.dir * self.speed * (0.4 + 1.1 * ctx.energy) * ctx.dt
        if self.hp > 1.0:
            self.hp = 1.0
            self._turn(1)
        elif self.hp < 0.0:
            self.hp = 0.0
            self._turn(0)
        ed = self.edges[self.cur]
        self.bright[ed["idx"][np.abs(ed["par"] - self.hp) < self.head]] = 1.0
        lit = self.bright > 0.01
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        out[lit] += self.bright[lit][:, None] * rgb[None, :]


class TriangleLacing(Element):
    """Lights the eight corner clusters (the truss ⊠ triangle detail) by spectrum + a chase."""

    blend = "add"

    def __init__(self, model, hue: float = 0.1, sat: float = 0.95):
        ci = np.where(model.corner_mask)[0]
        P = model.positions[ci]
        s = (P > 0).astype(int)
        self.ci = ci
        self.cid = (s[:, 0] * 4 + s[:, 1] * 2 + s[:, 2]).astype(int)
        self.hue, self.sat = hue, sat
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        f = ctx.features
        bl = getattr(f, "buckets_l", None)
        amp = np.asarray(bl[:8], np.float32) if (bl is not None and len(bl) >= 8) else np.full(8, 0.4, np.float32)
        self._t += ctx.dt * (0.5 + ctx.energy)
        chase = 0.5 + 0.5 * np.sin(2 * np.pi * (np.arange(8) / 8.0) - self._t)
        v = (amp * (0.4 + 0.6 * chase)).astype(np.float32)
        hue = (self.hue + 0.045 * self.cid + ctx.evo_hue) % 1.0
        out[self.ci] += hsv_to_rgb(hue, ctx.sat(self.sat), v[self.cid])


class CornerLightning(Element):
    """Hard arcs that crawl along contiguous runs of the cube's edges, re-striking."""

    blend = "add"

    def __init__(self, model, hue: float = 0.6, sat: float = 0.35):
        self.seq = _edge_sequence(model)
        self.m = len(self.seq)
        self.hue, self.sat = hue, sat
        self._env = EnvFollower(0.12)
        self._mask = np.arange(min(40, self.m))
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._t += ctx.dt
        if self._t > 0.18 or ctx.events("kick"):
            self._t = 0.0
            a = int(_RNG.integers(0, self.m))
            L = int(_RNG.integers(max(2, self.m // 8), max(3, self.m // 3)))
            self._mask = np.arange(a, a + L) % self.m
            self._env.trigger(1.0)
        v = self._env.step(ctx.dt)
        if v > 0.01:
            rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
            out[self.seq[self._mask]] += v * rgb


class TrussCurrent(Element):
    """Energy injected at points diffuses/decays along the edge frame (a current)."""

    blend = "add"

    def __init__(self, model, hue: float = 0.55, sat: float = 0.9):
        self.seq = _edge_sequence(model)
        self.m = len(self.seq)
        self.charge = np.zeros(self.m, np.float32)
        self.charge[: min(24, self.m)] = 1.0  # seed so there's current from the first frame
        self.hue, self.sat = hue, sat
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        c = 0.5 * self.charge + 0.25 * np.roll(self.charge, 1) + 0.25 * np.roll(self.charge, -1)
        c *= math.exp(-ctx.dt / 2.5)
        self._t += ctx.dt
        if self._t > 0.4 or ctx.events("kick"):
            self._t = 0.0
            p = int(_RNG.integers(0, self.m))
            c[p:p + 20] += 1.0
        self.charge = c
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        out[self.seq] += np.clip(c, 0, 1)[:, None] * rgb[None, :]


class NormalSun(Element):
    """A moving light orbits the cube; each LED shades by normal·light — directional 3-D shading."""

    blend = "add"

    def __init__(self, model, hue: float = 0.12, sat: float = 0.5, ambient: float = 0.08):
        nrm = getattr(model, "normal", getattr(model, "normals", None))
        self.nrm = nrm.astype(np.float32) if nrm is not None else None
        self.hue, self.sat, self.ambient = hue, sat, ambient

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        if self.nrm is None:
            return
        a = ctx.t * 0.3 * (0.5 + ctx.energy)
        el = 0.4 * math.sin(ctx.t * 0.21)
        L = np.array([math.cos(a) * math.cos(el), math.sin(el), math.sin(a) * math.cos(el)], np.float32)
        d = np.clip(self.nrm @ L, 0, 1).astype(np.float32)
        val = (self.ambient + (1 - self.ambient) * d) * (0.6 + 0.5 * ctx.energy)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


# --- E. Physical / waves / organic ------------------------------------------

class RippleTank(Element):
    """Expanding, interfering wave shells from impact points — water caustics."""

    blend = "add"

    def __init__(self, model, hue: float = 0.55, sat: float = 0.85, k: float = 8.0, speed: float = 0.8):
        self.P = _pn(model)
        self.hue, self.sat, self.k, self.speed = hue, sat, k, speed
        self.src = [[(_RNG.random(3) * 2 - 1).astype(np.float32), float(a)] for a in (0.0, 0.8)]
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._t += ctx.dt
        if ctx.events("kick") or self._t > 0.5:
            self._t = 0.0
            self.src.append([(_RNG.random(3) * 2 - 1).astype(np.float32), 0.0])
        field = np.zeros(len(self.P), np.float32)
        keep = []
        for o, age in self.src:
            age += ctx.dt
            if age > 2.5:
                continue
            keep.append([o, age])
            d = np.sqrt(((self.P - o) ** 2).sum(1))
            field += math.exp(-age * 0.9) * np.sin(self.k * d - self.speed * self.k * age) * np.exp(-d * 0.6)
        self.src = keep[-8:]
        val = np.clip(field, 0, 1).astype(np.float32) * (0.5 + 0.6 * ctx.energy)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


class Aurora(Element):
    """Vertical curtains of light (northern-lights) waving around the cube."""

    blend = "add"

    def __init__(self, model, sat: float = 0.9, base: float = 0.6):
        P = model.positions
        self.ang = (np.arctan2(P[:, 2], P[:, 0]) / (2 * np.pi)).astype(np.float32)
        self.hy = np.clip((P[:, 1] + model.cfg.half) / model.cfg.side_m, 0, 1).astype(np.float32)
        self.sat, self.base = sat, base

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        a = self.ang * 6.0 + 0.6 * np.sin(self.hy * 3.0 + t * 0.5) + t * 0.1
        curtain = (np.clip(np.sin(a * 2 * np.pi) * 0.5 + 0.5, 0, 1)) ** 2
        hue = (0.33 + 0.25 * self.hy + 0.05 * math.sin(t * 0.2) + ctx.evo_hue) % 1.0
        val = self.base * curtain * (0.35 + 0.7 * self.hy) * (0.5 + 0.6 * ctx.energy)
        out += hsv_to_rgb(hue, ctx.sat(self.sat), val.astype(np.float32))


class Accretion(Element):
    """Particles spiral INWARD toward a moving sink and vanish — an accretion disk."""

    blend = "add"

    def __init__(self, model, n: int = 60, hue: float = 0.05, sat: float = 0.9, width: float = 0.16):
        self.ang = (_RNG.random(n) * 2 * np.pi).astype(np.float32)
        self.rad = (0.5 + _RNG.random(n) * 1.0).astype(np.float32)
        self.yy = ((_RNG.random(n) * 2 - 1) * 0.7).astype(np.float32)
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        dt = min(ctx.dt, 0.05)
        self.ang += dt * (1.0 + 2.0 / (self.rad + 0.2)) * (0.5 + ctx.energy)
        self.rad -= dt * 0.25 * (0.5 + ctx.energy)
        resp = self.rad < 0.08
        if resp.any():
            self.rad[resp] = 0.6 + _RNG.random(int(resp.sum())) * 0.9
            self.ang[resp] = _RNG.random(int(resp.sum())) * 2 * np.pi
        sx, sz = 0.3 * math.sin(ctx.t * 0.3), 0.3 * math.cos(ctx.t * 0.3)
        px = self.rad * np.cos(self.ang) + sx
        pz = self.rad * np.sin(self.ang) + sz
        py = self.yy * self.rad
        dx = self.P[:, 0, None] - px[None, :]
        dy = self.P[:, 1, None] - py[None, :]
        dz = self.P[:, 2, None] - pz[None, :]
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (self.width ** 2)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class DipoleField(Element):
    """Field lines of a rotating magnetic dipole loop through the cube."""

    blend = "add"

    def __init__(self, model, hue: float = 0.6, sat: float = 0.85, lines: int = 5):
        self.P = _pn(model)
        self.hue, self.sat, self.lines = hue, sat, lines

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        a = ctx.t * 0.3
        m = np.array([math.sin(a), math.cos(a) * 0.7, math.cos(a) * 0.5], np.float32)
        m /= (np.linalg.norm(m) + 1e-9)
        P = self.P
        r = np.sqrt((P * P).sum(1)) + 1e-3
        cos = np.clip((P @ m) / r, -1, 1)
        sin2 = 1 - cos * cos + 1e-3
        bands = np.sin(self.lines * np.pi * (r / sin2))
        val = np.clip(1.0 - np.abs(bands) * 1.2, 0, 1) * np.exp(-r * 0.5)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          val.astype(np.float32) * (0.5 + 0.6 * ctx.energy))
