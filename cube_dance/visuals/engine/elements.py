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


class PlasmaField(Element):
    """Smooth flowing colour field over the whole cube (psychedelic oil-slick).

    Not beat-reactive -- a continuous interference pattern of sinusoids over the
    3-D position, with the hue rotating via evolution. Deliberately unlike the
    discrete beam/corner visuals.
    """

    blend = "add"

    def __init__(self, model, sat: float = 0.95, base: float = 0.55, hue_base: float = 0.0) -> None:
        P = (model.positions / model.cfg.side_m).astype(np.float32)
        self.x, self.y, self.z = P[:, 0], P[:, 1], P[:, 2]
        self.sat, self.base, self.hue_base, self.n = sat, base, hue_base, model.n

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        sc = 3.0 * (0.4 + ctx.size)
        a = np.sin(self.x * sc + t * 0.7)
        b = np.sin(self.z * sc - t * 0.9)
        c = np.sin((self.x + self.y + self.z) * sc * 0.6 + t * 0.5)
        field = (a + b + c) / 3.0
        hue = (self.hue_base + 0.3 * field + ctx.evo_hue) % 1.0
        val = (self.base * (0.55 + 0.45 * np.sin(field * 3.1 + t * 0.6)) * (0.7 + 0.5 * ctx.energy))
        out += hsv_to_rgb(hue.astype(np.float32), np.float32(ctx.sat(self.sat)), val.astype(np.float32))


class HeatField(Element):
    """A rising, flickering fire: white/yellow-hot at the base, red embers up top.

    Locked warm palette (the hue knob only *tints* it); flickers per-pixel and
    surges with the bass. Nothing like the rainbow spectrum visuals.
    """

    blend = "add"
    _rng = np.random.default_rng(7)

    def __init__(self, model, gain: float = 1.1) -> None:
        h = (model.positions[:, 1] + model.cfg.half) / model.cfg.side_m
        self.h = np.clip(h, 0.0, 1.0).astype(np.float32)
        self.phase = self._rng.uniform(0.0, 6.283, model.n).astype(np.float32)
        self.gain, self.n = gain, model.n

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        flick = 0.55 + 0.45 * np.sin(t * 9.0 + self.phase) * np.sin(t * 5.3 + self.phase * 1.7)
        bass = float(getattr(ctx.features, "bass", 0.0) or 0.0)
        reach = 0.55 + 0.6 * ctx.size  # flame height
        heat = np.clip((reach - self.h) / reach, 0.0, 1.0)
        f = np.clip(heat * (0.7 + 0.9 * bass + 0.3 * ctx.energy) * flick * self.gain, 0.0, 1.25)
        hue = (0.02 + 0.10 * f + ctx.evo_hue) % 1.0  # red -> yellow as it heats; evo tints
        sat = np.zeros_like(f) if ctx.mono else np.clip(1.05 - 0.9 * f, 0.0, 1.0)  # white-hot base
        out += hsv_to_rgb(hue.astype(np.float32), sat.astype(np.float32), np.clip(f * 1.15, 0.0, 1.0))


class DigitalRain(Element):
    """Matrix-style rain: bright heads fall down the cube, trailing upward.

    Discrete green streams (the hue knob recolours them); driven by treble. The
    'fall' (space) knob sets the speed. Sparse and downward -- a digital look.
    """

    blend = "add"

    def __init__(self, model, hue_base: float = 0.34, sat: float = 0.9,
                 drops: int = 5, trail: float = 0.22) -> None:
        h = (model.positions[:, 1] + model.cfg.half) / model.cfg.side_m
        self.h = np.clip(h, 0.0, 1.0).astype(np.float32)
        P = model.positions
        col = (np.round(P[:, 0] * 3).astype(int) * 31 + np.round(P[:, 2] * 3).astype(int) * 7)
        self.off = ((col % 17) / 17.0).astype(np.float32)  # per-column phase offset
        self.hue_base, self.sat, self.drops, self.trail, self.n = hue_base, sat, drops, trail, model.n

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        t = ctx.t
        speed = 0.30 + 0.6 * ctx.size
        tr = float(getattr(ctx.features, "treble", 0.0) or 0.0)
        bright = np.zeros(self.n, np.float32)
        K = self.drops
        for k in range(K):
            head = 1.0 - ((t * speed + self.off + k / float(K)) % 1.0)  # falls 1 -> 0
            d = self.h - head  # >0 above the head = trail
            bright = np.maximum(bright, np.where((d >= 0) & (d < self.trail), 1.0 - d / self.trail, 0.0))
        val = bright * (0.45 + 0.8 * tr + 0.4 * ctx.energy)
        hue = np.float32((self.hue_base + ctx.evo_hue) % 1.0)
        out += hsv_to_rgb(hue, np.float32(ctx.sat(self.sat)), val.astype(np.float32))


class SirenStrobe(Element):
    """Hard two-colour emergency strobe: the left/right halves swap on a fast pulse.

    Police/rave alarm energy -- hard cuts between two hues on opposite sides. The
    'rate' (space) knob sets the speed; surges with energy.
    """

    blend = "add"

    def __init__(self, model, hue_a: float = 0.0, hue_b: float = 0.62, sat: float = 1.0,
                 rate: float = 3.0) -> None:
        x = model.positions[:, 0]
        self.left = x < 0.0
        self.right = ~self.left
        self.hue_a, self.hue_b, self.sat, self.rate = hue_a, hue_b, sat, rate
        self._phase = 0.0

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        self._phase = (self._phase + self.rate * (0.4 + ctx.size) * ctx.dt) % 1.0
        sat = ctx.sat(self.sat)
        v = 0.85 + 0.15 * ctx.energy
        if self._phase < 0.5:
            out[self.left] += np.asarray(hsv_to_rgb((self.hue_a + ctx.evo_hue) % 1.0, sat, v), np.float32)
        else:
            out[self.right] += np.asarray(hsv_to_rgb((self.hue_b + ctx.evo_hue) % 1.0, sat, v), np.float32)


class Spiral(Element):
    """A 3-D (double) helix wrapping the cube vertically.

    Each LED lights by its proximity to a parametric helix curve, so the wireframe
    cube lights up *where the spiral intersects the structure*. With ``double`` a
    second, counter-rotating helix runs in a contrasting hue, and the points where
    the two helices **cross** glow white — the intersection of the two spirals.
    Rotation accelerates with energy; the radius pulses with the bass; kicks bloom it.
    """

    blend = "add"

    def __init__(self, model, radius: float = 1.25, turns: float = 2.5, width: float = 0.055,
                 hue: float = 0.0, hue_b: float = 0.5, sat: float = 0.95, double: bool = True,
                 base_speed: float = 0.16, intersect: float = 1.8, samples: int = 160) -> None:
        P = model.positions
        half = float(model.cfg.half)
        self.x = P[:, 0].astype(np.float32)
        self.y = P[:, 1].astype(np.float32)
        self.z = P[:, 2].astype(np.float32)
        self.half = half
        self.side = float(model.cfg.side_m)
        self.radius, self.turns, self.width = radius, turns, width
        self.hue, self.hue_b, self.sat = hue, hue_b, sat
        self.double, self.base_speed, self.intersect = double, base_speed, intersect
        self.samples = samples
        self._s = np.linspace(0.0, 1.0, samples, dtype=np.float32)
        self._phase = 0.0
        self._bloom = EnvFollower(0.25)

    def _proximity(self, R: float, w: float, direction: float, phase: float, density: float):
        """Per-LED brightness from the true 3-D distance to the helix curve.

        ``density`` (0..1) is how much of the helix has grown in, from the bottom;
        samples beyond it are pushed away so the spiral fills 0->100%.
        """
        theta = direction * (2.0 * np.pi * self.turns * self._s) + phase
        px = (R * np.cos(theta)).astype(np.float32)
        py = (-self.half + self.side * self._s).astype(np.float32)
        py = np.where(self._s <= density, py, np.float32(1e6))  # hide the un-grown tip
        pz = (R * np.sin(theta)).astype(np.float32)
        dx = self.x[:, None] - px[None, :]
        dy = self.y[:, None] - py[None, :]
        dz = self.z[:, None] - pz[None, :]
        md2 = (dx * dx + dy * dy + dz * dz).min(axis=1)
        return np.exp(-md2 / (w * w)).astype(np.float32)

    def apply(self, ctx: Context, out: np.ndarray) -> None:
        for e in ctx.events("kick"):
            self._bloom.trigger(e.strength)
        bloom = self._bloom.step(ctx.dt)
        self._phase += self.base_speed * (0.6 + 1.4 * ctx.energy) * ctx.dt * 2.0 * np.pi

        bass = float(getattr(ctx.features, "bass", 0.0) or 0.0)
        R = self.radius * self.half * (1.0 + 0.16 * bass)
        density = float(np.clip((ctx.size - 0.5) / 1.3, 0.0, 1.0))  # 'density' knob: 0->100%
        w = self.width * self.half * (1.0 + 0.7 * bloom)
        sat = ctx.sat(self.sat)

        a = self._proximity(R, w, 1.0, self._phase, density)
        rgb_a = np.asarray(hsv_to_rgb((self.hue + ctx.evo_hue) % 1.0, sat, 1.0), np.float32)
        out += a[:, None] * rgb_a[None, :]

        if self.double:
            b = self._proximity(R, w, -1.0, self._phase, density)
            rgb_b = np.asarray(hsv_to_rgb((self.hue_b + ctx.evo_hue) % 1.0, sat, 1.0), np.float32)
            out += b[:, None] * rgb_b[None, :]
            inter = (a * b) * (self.intersect * (1.0 + 2.5 * bloom))  # bright only where they cross
            out += inter[:, None]  # white intersection glow


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
