"""Round-2 effects (see docs/effect-ideas-2.md): 10 inspired by famous music
visualisations + 10 keyed off the physical truss. Each Element writes a continuous
contribution so its preset reads without transients.
"""

from __future__ import annotations

import math

import numpy as np

from ...patterns import hsv_to_rgb
from .context import Context, EnvFollower
from .element import Element
from .effects import _pn  # positions / half  (~[-1,1]^3)

_RNG = np.random.default_rng()


def _hy(model):
    return np.clip((model.positions[:, 1] + model.cfg.half) / model.cfg.side_m, 0, 1).astype(np.float32)


def _ang(model):
    P = model.positions
    return ((np.arctan2(P[:, 2], P[:, 0]) / (2 * np.pi)) % 1.0).astype(np.float32)


def _buckets(ctx, nb_default=8):
    bl = getattr(ctx.features, "buckets_l", None)
    if bl is not None and len(bl):
        return np.asarray(bl, np.float32)
    return np.full(nb_default, 0.4, np.float32)


# ============================ A — famous-inspired ===========================

class Oscilloscope(Element):
    """The live stereo waveform drawn as a 3-D curve (Jerobeam Fenderson / AVS scope)."""

    blend = "add"

    def __init__(self, model, hue=0.45, sat=0.9, width=0.16):
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx, out):
        w = getattr(ctx.features, "wave", None)
        if w is not None and len(w) >= 8:
            w = np.asarray(w, np.float32)
            L, R = w[:, 0], w[:, 1]
            ramp = np.linspace(-1, 1, len(L)).astype(np.float32)
            px, py, pz = L * 1.4, R * 1.4, ramp * (0.6 + 0.6 * ctx.size)
        else:  # fallback: a Lissajous figure from time
            s = np.linspace(0, 2 * np.pi, 160, dtype=np.float32)
            px = 1.15 * np.sin(3 * s + ctx.t)
            py = 1.15 * np.sin(2 * s)
            pz = 1.0 * np.sin(5 * s + ctx.t * 0.5)
        dx = self.P[:, 0, None] - px[None, :]
        dy = self.P[:, 1, None] - py[None, :]
        dz = self.P[:, 2, None] - pz[None, :]
        wd = self.width * (0.7 + ctx.size)
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (wd * wd)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class Spectrogram(Element):
    """A falling spectrogram: frequency bands scroll down the cube over time."""

    blend = "add"

    def __init__(self, model, sat=0.9):
        self.hy = _hy(model)
        self.sat = sat
        self._scroll = 0.0

    def apply(self, ctx, out):
        b = _buckets(ctx)
        nb = len(b)
        self._scroll = (self._scroll + ctx.dt * 0.25 * (0.5 + ctx.size)) % 1.0
        pos = (self.hy + self._scroll) % 1.0
        band = np.clip((pos * nb).astype(int), 0, nb - 1)
        val = b[band] * (0.4 + 0.8 * ctx.energy)
        out += hsv_to_rgb((pos + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


class Feedback(Element):
    """MilkDrop-style feedback: an injected colour spirals/zooms with decaying echoes."""

    blend = "add"

    def __init__(self, model, hue=0.0, sat=0.9):
        self.P = _pn(model)
        self.buf = np.zeros((model.n, 3), np.float32)
        self.hue, self.sat = hue, sat
        a, zoom = 0.06, 0.97
        ca, sa = math.cos(a), math.sin(a)
        tgt = np.stack([(self.P[:, 0] * ca + self.P[:, 2] * sa) * zoom,
                        self.P[:, 1] * zoom,
                        (-self.P[:, 0] * sa + self.P[:, 2] * ca) * zoom], 1)
        try:
            from scipy.spatial import cKDTree
            self.idx = cKDTree(self.P).query(tgt)[1]
        except Exception:  # noqa: BLE001
            self.idx = np.arange(model.n)
        self.corner = np.where(model.corner_mask)[0]

    def apply(self, ctx, out):
        self.buf = self.buf[self.idx] * math.exp(-ctx.dt / 0.5)  # warp + decay (feedback)
        bass = float(getattr(ctx.features, "bass", 0.0) or 0.0)
        col = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        self.buf[self.corner] += col * (0.25 + 0.7 * bass)  # inject at the corners
        np.clip(self.buf, 0, 1.6, out=self.buf)
        out += self.buf


class RadialSpectrum(Element):
    """Monstercat-style radial EQ: the spectrum wrapped around the cube by angle."""

    blend = "add"

    def __init__(self, model, sat=0.95):
        self.ang = _ang(model)
        self.sat = sat

    def apply(self, ctx, out):
        b = _buckets(ctx)
        nb = len(b)
        band = np.clip((self.ang * nb).astype(int), 0, nb - 1)
        val = b[band] * (0.4 + 0.8 * ctx.energy)
        out += hsv_to_rgb((self.ang + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


class Magnetosphere(Element):
    """Charged orbiting particles, each bound to a band, blooming with it (iTunes/Hodgin)."""

    blend = "add"
    _rng = np.random.default_rng()

    def __init__(self, model, n=44, hue=0.6, sat=0.85, width=0.16):
        self.ang = (self._rng.random(n) * 2 * np.pi).astype(np.float32)
        self.el = ((self._rng.random(n) * 2 - 1)).astype(np.float32)
        self.band = self._rng.integers(0, 8, n)
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx, out):
        b = _buckets(ctx)
        amp = b[np.clip(self.band, 0, len(b) - 1)]
        self.ang += ctx.dt * (0.6 + 1.4 * ctx.energy)
        rad = 0.7 + 0.6 * amp
        px, pz, py = rad * np.cos(self.ang), rad * np.sin(self.ang), self.el * (0.8 + 0.4 * amp)
        dx = self.P[:, 0, None] - px[None, :]
        dy = self.P[:, 1, None] - py[None, :]
        dz = self.P[:, 2, None] - pz[None, :]
        band = np.exp(-(dx * dx + dy * dy + dz * dz).min(1) / (self.width ** 2)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.5 * ctx.energy))


class Cymatics(Element):
    """Chladni standing-wave nodal pattern; the dominant pitch sets the node spacing."""

    blend = "add"

    def __init__(self, model, hue=0.55, sat=0.85):
        self.P = _pn(model) * np.float32(math.pi)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        b = _buckets(ctx)
        k = 1.0 + 3.0 * (int(np.argmax(b)) / max(len(b) - 1, 1))  # wave number from dominant band
        f = np.cos(k * self.P[:, 0]) * np.cos(k * self.P[:, 1]) * np.cos(k * self.P[:, 2])
        val = np.clip(np.abs(f) - 0.25, 0, 1) * (0.5 + 0.6 * ctx.energy)  # antinodes bright, nodes dark
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


class Tunnel(Element):
    """Demoscene tunnel: concentric rings rushing out from the centre axis."""

    blend = "add"

    def __init__(self, model, hue=0.6, sat=0.85):
        P = model.positions
        r = np.sqrt(P[:, 0] ** 2 + P[:, 2] ** 2)
        self.r = (r / (float(r.max()) or 1.0)).astype(np.float32)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        t = ctx.t * (0.5 + 1.6 * ctx.energy)
        rings = 0.5 + 0.5 * np.sin((self.r * 7.0 - t) * 2 * np.pi)
        val = rings * (0.4 + 0.7 * ctx.energy)
        out += hsv_to_rgb((self.r * 0.5 + ctx.evo_hue + t * 0.04) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


class LarsonScanner(Element):
    """The Knight Rider / Cylon sweeping bar with a fading tail."""

    blend = "add"

    def __init__(self, model, axis=0, hue=0.0, sat=1.0, width=0.12, speed=0.6):
        half = float(model.cfg.half)
        self.c = np.clip((model.positions[:, axis] + half) / model.cfg.side_m, 0, 1).astype(np.float32)
        self.hue, self.sat, self.width, self.speed = hue, sat, width, speed
        self.buf = np.zeros(model.n, np.float32)
        self._ph, self._dir = 0.0, 1.0

    def apply(self, ctx, out):
        self._ph += self._dir * self.speed * (0.5 + ctx.energy) * ctx.dt
        if self._ph > 1.0:
            self._ph, self._dir = 1.0, -1.0
        elif self._ph < 0.0:
            self._ph, self._dir = 0.0, 1.0
        head = np.clip(1.0 - np.abs(self.c - self._ph) / self.width, 0, 1) ** 1.5
        self.buf *= math.exp(-ctx.dt / 0.22)  # fading tail
        self.buf = np.maximum(self.buf, head.astype(np.float32))
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), self.buf * (0.6 + 0.4 * ctx.energy))


class Blinder(Element):
    """Festival white strobe / blinder: beat-synced full-cube flash + a base-ring blinder."""

    blend = "add"

    def __init__(self, model):
        half = float(model.cfg.half)
        self.base = np.where(model.positions[:, 1] < -half * 0.55)[0]
        self.n = model.n
        self._env = EnvFollower(0.07)

    def apply(self, ctx, out):
        for e in ctx.events("kick"):
            self._env.trigger(1.0)
        lfo = 0.5 + 0.5 * math.sin(ctx.t * 2 * np.pi * (1.0 + ctx.energy))
        v = max(self._env.step(ctx.dt), (1.0 if lfo > 0.82 else 0.0) * ctx.energy, 0.12 * ctx.energy)
        white = np.array([v, v, v], np.float32)
        out += white
        out[self.base] += 0.6 * white


class PanelSequencer(Element):
    """Daft-Punk-pyramid / deadmau5-Cube style chevrons climbing the faces."""

    blend = "add"

    def __init__(self, model, hue=0.5, sat=0.95):
        self.hy = _hy(model)
        self.ang = _ang(model)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        t = ctx.t * (0.4 + ctx.energy)
        zig = np.abs((self.ang * 4.0) % 1.0 - 0.5)  # chevron shape around the cube
        c = (self.hy - zig * 0.5 - t * 0.2) % 0.5
        val = (c < 0.13).astype(np.float32) * (0.5 + 0.6 * ctx.energy)
        hue = (self.hue + 0.12 * np.floor((self.hy - t * 0.2) / 0.5) + ctx.evo_hue) % 1.0
        out += hsv_to_rgb(hue, ctx.sat(self.sat), val)


# ============================ B — structure-aware ===========================

def _edge_struct(model):
    """Per edge-LED arrays + per-edge corner ids (corner = sign of position)."""
    eidx = np.where(model.edge_mask)[0]
    eid = model.element_id[eidx]
    par = model.param[eidx].astype(np.float32)
    pos = model.positions[eidx]

    def corner(p):
        return int(p[0] > 0) * 4 + int(p[1] > 0) * 2 + int(p[2] > 0)

    uniq = list(np.unique(eid))
    ecorner = {}  # eid -> (c0, c1)
    for e in uniq:
        sel = np.where(eid == e)[0]
        order = sel[np.argsort(par[sel])]
        ecorner[e] = (corner(pos[order[0]]), corner(pos[order[-1]]))
    return eidx, eid, par, pos, uniq, ecorner


class BeamBars(Element):
    """Per-beam spectrum bars: each of the 12 beams is a band, filling from its corner."""

    blend = "add"

    def __init__(self, model, sat=0.95):
        self.eidx, eid, self.par, _, uniq, _ = _edge_struct(model)
        bandof = {e: i % 8 for i, e in enumerate(uniq)}
        self.band = np.array([bandof[e] for e in eid])
        self.sat = sat

    def apply(self, ctx, out):
        b = _buckets(ctx)
        bnd = np.clip(self.band, 0, len(b) - 1)
        level = b[bnd]
        val = (self.par <= level).astype(np.float32) * (0.5 + 0.6 * ctx.energy)
        hue = (0.06 * bnd + ctx.evo_hue) % 1.0
        out[self.eidx] += hsv_to_rgb(hue, ctx.sat(self.sat), val)


class LacingWave(Element):
    """A wave sweeping across the corner truss (the ⊠ triangles) along the main diagonal."""

    blend = "add"

    def __init__(self, model, hue=0.1, sat=0.95):
        ci = np.where(model.corner_mask)[0]
        self.ci = ci
        self.diag = ((model.positions[ci].sum(1)) / (3 * model.cfg.half)).astype(np.float32)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        t = ctx.t * (0.5 + ctx.energy)
        wave = 0.5 + 0.5 * np.sin((self.diag * 3.0 - t) * 2 * np.pi)
        val = (wave ** 3) * (0.4 + 0.7 * ctx.energy)
        out[self.ci] += hsv_to_rgb((self.hue + 0.2 * self.diag + ctx.evo_hue) % 1.0,
                                   ctx.sat(self.sat), val.astype(np.float32))


class CornerImpulse(Element):
    """A pulse expands from a (rotating) corner across the frame — a signal through the truss."""

    blend = "add"

    def __init__(self, model, hue=0.6, sat=0.9, width=0.45):
        self.P = _pn(model)
        half = 1.0
        self.corners = np.array([[(half if (c >> b) & 1 else -half) for b in (2, 1, 0)] for c in range(8)], np.float32)
        self.hue, self.sat, self.width = hue, sat, width
        self._src, self._front, self._t = 0, 0.0, 0.0

    def apply(self, ctx, out):
        self._t += ctx.dt
        self._front += ctx.dt * (0.8 + 1.5 * ctx.energy)
        if self._front > 2.6 or ctx.events("kick"):
            self._front = 0.0
            self._src = int(_RNG.integers(8))
        d = np.sqrt(((self.P - self.corners[self._src]) ** 2).sum(1))
        val = np.exp(-((d - self._front) / self.width) ** 2).astype(np.float32) * (0.5 + 0.5 * ctx.energy)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


class FaceSpin(Element):
    """Lights one cube face at a time, rotating around the cube."""

    blend = "add"

    def __init__(self, model, hue=0.33, sat=0.9):
        self.P = _pn(model)
        self.faces = [(0, 1), (0, -1), (2, 1), (2, -1), (1, 1), (1, -1)]  # (axis, sign)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        seq = ctx.t * (0.6 + ctx.energy)
        i = int(seq) % len(self.faces)
        nxt = (i + 1) % len(self.faces)
        frac = seq - math.floor(seq)
        val = np.zeros(len(self.P), np.float32)
        for fi, w in ((i, 1.0 - frac), (nxt, frac)):  # crossfade between faces
            ax, sg = self.faces[fi]
            val = np.maximum(val, w * np.clip((self.P[:, ax] * sg - 0.78) / 0.22, 0, 1))
        out += hsv_to_rgb((self.hue + 0.13 * i + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          (val * (0.5 + 0.5 * ctx.energy)).astype(np.float32))


class BarberPole(Element):
    """Stripes wind along + around each beam (the parallel chord rows offset in phase)."""

    blend = "add"

    def __init__(self, model, hue=0.5, sat=0.9, coils=3.0):
        eidx, eid, par, pos, uniq, _ = _edge_struct(model)
        self.eidx, self.par = eidx, par
        around = np.zeros(len(eidx), np.float32)
        for e in uniq:
            sel = np.where(eid == e)[0]
            p = pos[sel]
            d = p[-1] - p[0] if len(p) > 1 else np.array([1.0, 0, 0])
            d = d / (np.linalg.norm(d) + 1e-9)
            rel = p - p.mean(0)
            perp = rel - np.outer(rel @ d, d)
            # a stable basis in the perpendicular plane
            b1 = np.cross(d, [0, 1, 0])
            if np.linalg.norm(b1) < 1e-3:
                b1 = np.cross(d, [1, 0, 0])
            b1 /= np.linalg.norm(b1) + 1e-9
            b2 = np.cross(d, b1)
            around[sel] = (np.arctan2(perp @ b2, perp @ b1) / (2 * np.pi)).astype(np.float32)
        self.around = around
        self.hue, self.sat, self.coils = hue, sat, coils

    def apply(self, ctx, out):
        t = ctx.t * (0.5 + ctx.energy)
        phase = self.par * self.coils + self.around - t
        val = (0.5 + 0.5 * np.sin(phase * 2 * np.pi)) ** 2 * (0.5 + 0.5 * ctx.energy)
        out[self.eidx] += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val.astype(np.float32))


class WireframeBuild(Element):
    """The cube draws itself edge-by-edge then dissolves (a self-assembling wireframe)."""

    blend = "add"

    def __init__(self, model, hue=0.55, sat=0.9):
        eidx = np.where(model.edge_mask)[0]
        order = np.lexsort((model.param[eidx], model.element_id[eidx]))
        self.seq = eidx[order]
        self.along = (np.arange(len(self.seq)) / max(len(self.seq), 1)).astype(np.float32)
        self.hue, self.sat = hue, sat

    def apply(self, ctx, out):
        phase = 0.5 + 0.5 * math.sin(ctx.t * 0.25 * (0.6 + ctx.energy))  # build / unbuild breath
        val = (self.along <= phase).astype(np.float32)
        tip = np.clip(1.0 - np.abs(self.along - phase) / 0.05, 0, 1)  # bright drawing tip
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        out[self.seq] += (0.55 * val + 0.45 * tip)[:, None] * rgb[None, :] * (0.6 + 0.4 * ctx.energy)


class RingRotate(Element):
    """Top and bottom rings chase in opposite directions; the posts bridge them."""

    blend = "add"

    def __init__(self, model, hue=0.4, sat=0.9, width=0.1):
        self.hy = _hy(model)
        self.ang = _ang(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx, out):
        t = ctx.t * (0.4 + 1.0 * ctx.energy)
        d_top = np.abs(((self.ang - t) % 1.0) - 0.0)
        d_bot = np.abs(((self.ang + t) % 1.0) - 0.0)
        d_top = np.minimum(d_top, 1 - d_top)
        d_bot = np.minimum(d_bot, 1 - d_bot)
        top = np.clip(1 - d_top / self.width, 0, 1) * np.clip((self.hy - 0.5) / 0.5, 0, 1)
        bot = np.clip(1 - d_bot / self.width, 0, 1) * np.clip((0.5 - self.hy) / 0.5, 0, 1)
        val = np.maximum(top, bot).astype(np.float32) * (0.5 + 0.5 * ctx.energy)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


class GravityDrip(Element):
    """Light drips down the four posts under gravity and pools at the base ring."""

    blend = "add"
    _rng = np.random.default_rng()

    def __init__(self, model, hue=0.55, sat=0.9, drops=10):
        self.hy = _hy(model)
        P = model.positions
        self.col = (np.round(P[:, 0] / (0.3 * model.cfg.half)).astype(int) * 97
                    + np.round(P[:, 2] / (0.3 * model.cfg.half)).astype(int))
        self.cols = np.unique(self.col)
        self.hue, self.sat = hue, sat
        self.dy = np.full(len(self.cols), 2.0, np.float32)  # drop height per column (>1 inactive)
        self.dy[: min(4, len(self.cols))] = np.linspace(1.0, 0.5, min(4, len(self.cols)), dtype=np.float32)
        self.vy = np.zeros(len(self.cols), np.float32)
        self.pool = 0.0
        self._cidx = {c: i for i, c in enumerate(self.cols)}
        self.colidx = np.array([self._cidx[c] for c in self.col])

    def apply(self, ctx, out):
        g = 1.6
        active = self.dy < 1.5
        self.vy[active] += g * ctx.dt
        self.dy[active] -= self.vy[active] * ctx.dt
        landed = active & (self.dy < 0.0)
        self.pool = min(0.5, self.pool + 0.06 * int(landed.sum()))
        self.dy[landed] = 2.0
        # spawn
        idle = np.where(self.dy >= 1.5)[0]
        if len(idle) and (ctx.events("kick") or _RNG.random() < 0.06 + 0.1 * ctx.energy):
            k = idle[int(_RNG.integers(len(idle)))]
            self.dy[k] = 1.05
            self.vy[k] = 0.0
        self.pool = max(0.0, self.pool - 0.25 * ctx.dt)
        head = self.dy[self.colidx]
        d = self.hy - head
        val = np.where((head < 1.5) & (d >= -0.04) & (d < 0.22), np.clip(1 - np.abs(d) / 0.18, 0, 1), 0.0)
        val = np.maximum(val, self.pool * np.clip((0.12 - self.hy) / 0.12, 0, 1))  # pool at base
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          (val * (0.5 + 0.6 * ctx.energy)).astype(np.float32))


class DiagonalSweep(Element):
    """A plane sweeps along the cube's face-diagonal directions (rhyming with the lacing)."""

    blend = "add"

    def __init__(self, model, hue=0.7, sat=0.9, width=0.14):
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width
        self.dirs = [np.array(d, np.float32) / math.sqrt(2) for d in
                     [(1, 0, 1), (1, 0, -1), (0, 1, 1), (1, 1, 0)]]

    def apply(self, ctx, out):
        t = ctx.t
        n = self.dirs[int(t * 0.2) % len(self.dirs)]
        d = np.abs(self.P @ n - 1.2 * math.sin(t * 0.5))
        band = np.clip(1.0 - d / (self.width * (0.6 + ctx.size)), 0, 1).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), band * (0.6 + 0.4 * ctx.energy))


class ModalResonance(Element):
    """The truss rings: a structural vibration mode-shape brightens with the bass."""

    blend = "add"

    def __init__(self, model, hue=0.05, sat=0.85):
        self.u = (np.clip((model.positions + model.cfg.half) / model.cfg.side_m, 0, 1) * math.pi).astype(np.float32)
        self.hue, self.sat = hue, sat
        self._env = EnvFollower(0.4)
        self._mode = 0

    def apply(self, ctx, out):
        for e in ctx.events("kick"):
            self._env.trigger(1.0)
            self._mode = int(_RNG.integers(1, 4))
        bass = float(getattr(ctx.features, "bass", 0.0) or 0.0)
        amp = max(self._env.step(ctx.dt), 0.3 + 0.7 * bass)
        m = max(1, self._mode)
        shape = np.sin(m * self.u[:, 0]) * np.sin(m * self.u[:, 1]) * np.sin(m * self.u[:, 2])
        val = (np.abs(shape) * amp * (0.5 + 0.6 * ctx.energy)).astype(np.float32)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), val)


# ============================ DUSTLIGHT signature ===========================

class DriftMotes(Element):
    """Warm embers / fireflies drifting up through the cube, twinkling — the bush at night."""

    blend = "add"
    _rng = np.random.default_rng()

    def __init__(self, model, n=42, hue=0.08, sat=0.8, width=0.12):
        self.pos = ((self._rng.random((n, 3)) * 2 - 1) * 0.9).astype(np.float32)
        self.phase = (self._rng.random(n) * 6.283).astype(np.float32)
        self.drift = ((self._rng.random((n, 2)) * 2 - 1) * 0.08).astype(np.float32)
        self.P = _pn(model)
        self.hue, self.sat, self.width = hue, sat, width

    def apply(self, ctx, out):
        dt = min(ctx.dt, 0.05)
        self.pos[:, 1] += (0.12 + 0.25 * ctx.energy) * dt          # rise
        self.pos[:, 0] += (self.drift[:, 0] + 0.05 * np.sin(ctx.t * 0.7 + self.phase)) * dt
        self.pos[:, 2] += self.drift[:, 1] * dt
        top = self.pos[:, 1] > 1.1                                  # recycle at the top
        k = int(top.sum())
        if k:
            self.pos[top, 1] = -1.1
            self.pos[top, 0] = (self._rng.random(k) * 2 - 1) * 0.9
            self.pos[top, 2] = (self._rng.random(k) * 2 - 1) * 0.9
        tw = 0.45 + 0.55 * np.sin(ctx.t * 3.0 + self.phase)         # twinkle
        dx = self.P[:, 0, None] - self.pos[:, 0][None, :]
        dy = self.P[:, 1, None] - self.pos[:, 1][None, :]
        dz = self.P[:, 2, None] - self.pos[:, 2][None, :]
        glow = (np.exp(-(dx * dx + dy * dy + dz * dz) / (self.width * self.width)) * tw[None, :]).max(1)
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat),
                          (glow * (0.4 + 0.5 * ctx.energy)).astype(np.float32))


class Sunrise(Element):
    """A dawn gradient: a horizon line rises (gold below, indigo above) and blooms — the sunrise."""

    blend = "add"

    def __init__(self, model, sat=0.85):
        self.hy = _hy(model)
        self.sat = sat
        self._t = 0.0

    def apply(self, ctx, out):
        self._t += ctx.dt * 0.05
        sun = float(np.clip(0.15 + 0.55 * ctx.energy + 0.25 * math.sin(self._t), 0.0, 1.0))  # rising horizon
        glow = np.exp(-((self.hy - sun) * 2.6) ** 2)                     # bright band at the line
        warm = np.clip((sun - self.hy) * 1.5, 0, 1)                      # gold wash below
        hue = (0.05 + 0.62 * np.clip((self.hy - sun) * 0.9 + 0.45, 0, 1)).astype(np.float32)  # gold -> indigo
        val = np.clip(0.18 + 0.75 * glow + 0.45 * warm, 0, 1) * (0.4 + 0.7 * ctx.energy)
        out += hsv_to_rgb(hue, ctx.sat(self.sat), val.astype(np.float32))
