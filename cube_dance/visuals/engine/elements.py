"""Built-in visual elements. Each writes its contribution into the buffer."""

from __future__ import annotations

import math

import numpy as np

from ...geometry import build_edges
from ...patterns import hsv_to_rgb
from .context import Context, EnvFollower
from .element import Element, blend_into


class BassCorners(Element):
    """Corners glow with bass, split left/right by channel (warm)."""

    blend = "max"

    def __init__(self, model, hue: float = 0.0, sat: float = 0.95) -> None:
        x = model.positions[:, 0]
        self.cl = model.corner_mask & (x < 0)
        self.cr = model.corner_mask & (x >= 0)
        self.hue, self.sat = hue, sat

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        warm = (self.hue + ctx.evo_hue) % 1.0
        sat = ctx.sat(self.sat)
        f = ctx.features
        blend_into(out, self.cl, np.asarray(hsv_to_rgb(warm, sat, float(f.bass_l)), np.float32), self.blend)
        blend_into(out, self.cr, np.asarray(hsv_to_rgb(warm, sat, float(f.bass_r)), np.float32), self.blend)


class SpectrumBeams(Element):
    """Beams = a stereo spectrum running along each beam."""

    blend = "max"

    def __init__(self, model, n_buckets: int, sat: float = 0.9, spread: float = 0.78) -> None:
        side = {e.index: (2 if e.axis == 0 else (0 if e.fixed[0] < 0 else 1)) for e in build_edges()}
        self.idx = np.where(model.edge_mask)[0]
        self.bucket = np.clip((model.param[self.idx] * n_buckets).astype(int), 0, n_buckets - 1)
        self.side = np.array([side[int(e)] for e in model.element_id[self.idx]])
        self.hue_base = (self.bucket / max(n_buckets, 1)) * spread
        self.n_buckets, self.sat = n_buckets, sat

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        f = ctx.features
        bl = f.buckets_l if f.buckets_l is not None else np.zeros(self.n_buckets, np.float32)
        br = f.buckets_r if f.buckets_r is not None else np.zeros(self.n_buckets, np.float32)
        mono = 0.5 * (bl + br)
        val = np.where(self.side == 0, bl[self.bucket],
                       np.where(self.side == 1, br[self.bucket], mono[self.bucket])).astype(np.float32)
        hue = (self.hue_base + ctx.evo_hue) % 1.0
        blend_into(out, self.idx, hsv_to_rgb(hue, ctx.sat(self.sat), val), self.blend)


class KickPulse(Element):
    """Flash a region on every kick (decaying)."""

    blend = "add"

    def __init__(self, model, region: str = "corners", hue: float = 0.0, sat: float = 0.0,
                 release: float = 0.16, gain: float = 1.0) -> None:
        if region == "corners":
            self.idx = np.where(model.corner_mask)[0]
        elif region == "beams":
            self.idx = np.where(model.edge_mask)[0]
        else:
            self.idx = None  # whole cube
        self.env = EnvFollower(release)
        self.hue, self.sat, self.gain = hue, sat, gain

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        for e in ctx.events("kick"):
            self.env.trigger(e.strength)
        v = self.env.step(ctx.dt) * self.gain
        if v <= 0.002:
            return
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), min(1.0, v)), np.float32)
        blend_into(out, self.idx, rgb, self.blend)


class HatSparkle(Element):
    """Twinkle random beam LEDs on every hat."""

    blend = "add"

    def __init__(self, model, count: int = 26, release: float = 0.09, seed: int = 1) -> None:
        self.edge_idx = np.where(model.edge_mask)[0]
        self.spark = np.zeros(model.n, np.float32)
        self.count, self.release = count, release
        self._rng = np.random.default_rng(seed)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        if ctx.dt > 0:
            self.spark *= math.exp(-ctx.dt / self.release)
        count = max(1, int(round(self.count * ctx.size)))
        for e in ctx.events("hat"):
            pick = self._rng.choice(self.edge_idx, size=min(count, len(self.edge_idx)), replace=False)
            self.spark[pick] = np.maximum(self.spark[pick], e.strength)
        lit = self.spark > 0.01
        if lit.any():
            out[lit] += self.spark[lit][:, None]  # white sparkle


class Sweep(Element):
    """A soft band of light travelling along an axis (default vertical)."""

    blend = "add"

    def __init__(self, model, axis: int = 1, rate: float = 0.25, width: float = 0.12,
                 hue: float = 0.55, sat: float = 0.85, gain: float = 0.8) -> None:
        h = (model.positions[:, axis] + model.cfg.half) / model.cfg.side_m
        self.h = np.clip(h, 0.0, 1.0).astype(np.float32)
        self.rate, self.width, self.hue, self.sat, self.gain = rate, width, hue, sat, gain
        self._phase = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._phase = (self._phase + self.rate * ctx.dt) % 1.0
        width = max(0.01, self.width * ctx.size)
        band = np.exp(-((self.h - self._phase) / width) ** 2) * self.gain * (0.35 + 0.65 * ctx.energy)
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        out += band[:, None] * rgb[None, :]


class Chase(Element):
    """A light running around the cube (rotating about the vertical axis)."""

    blend = "add"

    def __init__(self, model, rate: float = 0.3, width: float = 0.07,
                 hue: float = 0.33, sat: float = 0.9, gain: float = 0.8) -> None:
        ang = (np.arctan2(model.positions[:, 2], model.positions[:, 0]) / (2 * np.pi)) % 1.0
        self.ang = ang.astype(np.float32)
        self.rate, self.width, self.hue, self.sat, self.gain = rate, width, hue, sat, gain
        self._phase = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._phase = (self._phase + self.rate * ctx.dt) % 1.0
        width = max(0.01, self.width * ctx.size)
        d = np.abs((self.ang - self._phase + 0.5) % 1.0 - 0.5)  # wrap-around distance
        band = np.exp(-(d / width) ** 2) * self.gain * (0.35 + 0.65 * ctx.energy)
        rgb = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), 1.0), np.float32)
        out += band[:, None] * rgb[None, :]


class Pulse(Element):
    """Whole-cube colour body that breathes with energy/bass (gives presets weight)."""

    blend = "add"

    def __init__(self, model, hue: float = 0.6, sat: float = 0.7, base: float = 0.06,
                 gain: float = 0.5, react: str = "energy") -> None:
        self.n = model.n
        self.hue, self.sat, self.base, self.gain, self.react = hue, sat, base, gain, react

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        drive = float(getattr(ctx.features, "bass", 0.0) or 0.0) if self.react == "bass" else ctx.energy
        b = self.base + self.gain * drive
        out += hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, ctx.sat(self.sat), np.full(self.n, b, np.float32))


def _region_idx(model, region: str):
    if region == "corners":
        return np.where(model.corner_mask)[0]
    if region == "beams":
        return np.where(model.edge_mask)[0]
    return None  # whole cube


# --- Transient trigger elements (spawned by preset pad triggers) -------------

class ColorStab(Element):
    """A decaying coloured flash over a region -- the default pad hit."""

    def __init__(self, model, color, gain: float = 1.0, release: float = 0.28,
                 region: str = "all") -> None:
        self.idx = _region_idx(model, region)
        self.color = np.asarray(color, np.float32)
        self.env = EnvFollower(release); self.env.trigger(max(0.15, gain))

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        v = self.env.step(ctx.dt)
        if v <= 0.004:
            self.done = True
            return
        blend_into(out, self.idx, self.color * min(1.0, v), "add")


class StrobeBurst(Element):
    """A short series of sharp flashes (white or coloured)."""

    def __init__(self, model, color, gain: float = 1.3, flashes: int = 5,
                 interval: float = 0.07, region: str = "all") -> None:
        self.idx = _region_idx(model, region)
        self.color = np.asarray(color, np.float32) * gain
        self.flashes, self.interval = flashes, interval
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._t += ctx.dt
        if self._t >= self.flashes * self.interval:
            self.done = True
            return
        if (self._t % self.interval) / self.interval < 0.5:  # on half of each cycle
            blend_into(out, self.idx, self.color, "add")


class RiserSweep(Element):
    """A bright band that sweeps up the cube while brightening, then ends (a build)."""

    def __init__(self, model, color, dur: float = 1.4, gain: float = 1.0,
                 width: float = 0.16, axis: int = 1) -> None:
        h = (model.positions[:, axis] + model.cfg.half) / model.cfg.side_m
        self.h = np.clip(h, 0.0, 1.0).astype(np.float32)
        self.color = np.asarray(color, np.float32)
        self.dur, self.gain, self.width = dur, gain, width
        self._t = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._t += ctx.dt
        if self._t >= self.dur:
            self.done = True
            return
        p = self._t / self.dur
        band = np.exp(-((self.h - p) / self.width) ** 2) * self.gain * (0.3 + 0.7 * p)
        out += band[:, None] * self.color[None, :]


class SparkBurst(Element):
    """A burst of random sparkles across the beams, decaying away."""

    _rng = np.random.default_rng()

    def __init__(self, model, color, count: int = 36, release: float = 0.5) -> None:
        edge = np.where(model.edge_mask)[0]
        self.idx = self._rng.choice(edge, size=min(count, len(edge)), replace=False)
        self.color = np.asarray(color, np.float32)
        self.env = EnvFollower(release); self.env.trigger(1.0)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        v = self.env.step(ctx.dt)
        if v <= 0.01:
            self.done = True
            return
        out[self.idx] += self.color * v


class AmbientWash(Element):
    """A faint always-on evolving wash so the cube never reads fully dead."""

    blend = "add"

    def __init__(self, model, base: float = 0.05, sat: float = 0.6) -> None:
        self.base, self.sat, self.n = base, sat, model.n
        self.h = ((model.positions[:, 1] + model.cfg.half) / model.cfg.side_m).astype(np.float32)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        b = self.base * (0.4 + 0.6 * ctx.energy)
        hue = (self.h * 0.2 * ctx.size + ctx.evo_hue) % 1.0
        out += hsv_to_rgb(hue, ctx.sat(self.sat), np.full(self.n, b, np.float32))
