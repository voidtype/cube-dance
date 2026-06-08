r"""``atlas`` — THE REFERENCE PLUGIN (the cube as a 3-D map of the sound).

This is the *default* effect, and it is written to be read. Open it in the editor
(``</> Edit Python``) and go top-to-bottom: it is the template for writing your
own plugin. It does two things at once —

  1. APPORTIONS SOUND ONTO SPACE. The cube becomes a 3-D spectrum analyser:
     bass lives at the BASE, treble at the TOP (height -> frequency); the LEFT
     half shows the left audio channel and the RIGHT half the right (x -> stereo);
     the raw waveform rings around the vertical axis as an oscilloscope; kicks
     fire a shockwave from the centre. You literally SEE the stereo spectrum in 3-D.

  2. ENUMERATES EVERYTHING A PLUGIN AUTHOR CAN TOUCH — every output of the FFT,
     every field of the per-frame Context, every piece of cube geometry, and the
     whole colour/helper toolkit — each used at least once and commented inline.

================================================================================
THE ENVIRONMENT — everything you get, and where it comes from
================================================================================

A) THE MODEL (cube geometry — fixed, precompute from it ONCE in __init__):
     model.positions   (N,3) float32  x,y,z metres of each of the N=9,744 LEDs,
                                       centred on the origin; cube spans [-half,+half].
     model.corner_mask (N,)  bool      True for the 8 corner-cluster LEDs.
     model.edge_mask   (N,)  bool      True for the 12 edge LEDs.
     model.param       (N,)  float32   each LED's 0..1 position ALONG its run
                                       (use for chases / sweeps / play-heads).
     model.element_id  (N,)  int       which physical run (the 12 edges) an LED is on.
     model.cfg.half    float           cube half-size (1.30 m); .side_m is the full side.
     model.n           int             LED count (9,744).

B) THE CONTEXT (ctx — fresh every frame, read it in apply()):
     ctx.t, ctx.dt                     seconds: absolute clock, and delta since last frame.
     ctx.features                      the analysed audio THIS frame (see C).
     ctx.energy                        smoothed overall loudness 0..1 (slower than level).
     ctx.density                       smoothed onset density 0..1 (how busy it is).
     ctx.evo_hue                       the global hue (your 'palette' knob + a slow drift).
     ctx.size                          spatial-extent multiplier (your 'depth' knob / SIZE btn).
     ctx.mono                          CAPTURE button -> render stark/white; honour via ctx.sat().
     ctx.events('kick')                onset Events this frame of a kind (.kind / .strength).
     ctx.beat                          a rough beat phase 0..1 (property).
     ctx.sat(s)                        saturation that collapses to 0 when mono is set.

C) THE FFT — EVERY output of the analyser (ctx.features). This plugin uses them ALL:
     level                             overall RMS loudness 0..1.
     bass / mid / treble               three broad mono bands 0..1.
     bass_l / bass_r                   per-CHANNEL bass -> the left/right corner split.
     buckets_l[8] / buckets_r[8]       an 8-band spectrum PER CHANNEL -> the spatial spectrum.
     beat                              beat phase 0..1.
     events                            classified onsets (kick/hat/snare/perc).
     wave                              a short (m,2) stereo waveform -> the 3-D oscilloscope.

D) THE TOOLKIT (import from the engine — see the imports below):
     hsv_to_rgb(h,s,v)                 vectorised HSV->RGB; h/s/v may be scalars OR (N,)
                                       arrays; returns 0..1 (an (N,3) when any input is an array).
     blend_into(out, idx, rgb, mode)   composite rgb into out at indices idx ('add' or 'max').
     EnvFollower(release_s)            fast-attack / slow-release envelope -> snappy hits.
     lfo(shape, phase)                 unipolar 0..1 LFO ('sine' / 'tri' / 'saw'), phase in cycles.

E) THE LIBRARY (ready-made elements to compose instead of, or alongside, your own):
     cube_dance/visuals/engine/elements.py  -> BassCorners, SpectrumBeams, Pulse, Sweep,
         Chase, Comet, Shockwave, SparkBurst, ColorStab, HeldGlow, AmbientWash, ... (~26)
     cube_dance/visuals/engine/effects.py   -> the 3-D / fractal ones: Mandelbulb, Aurora,
         EdgeSnake, RippleTank, GameOfLife3D, Tesseract, ... (~22)
     cube_dance/visuals/engine/effects2.py  -> the round-2 set (scope, tunnel, cymatics, ...).
   A preset's ``build(engine)`` just calls ``engine.add(...)`` on any mix of these
   and/or your own Element (below). Full power: an element is plain numpy — it may
   do ANY per-pixel maths it likes into the (N,3) buffer.

================================================================================
THE MATHS
================================================================================
Beyond numpy this leans on ``math`` (the stdlib maths library) for scalar trig /
exp / tau, and — as a bonus — on ``scipy.special.j0`` (a Bessel function) for clean
concentric "cymatic" rings. scipy ships with the engine (a desktop dependency, and
loaded in the browser), but we import it defensively so the plugin still loads if
it is ever missing. The field maths on show: distance fields (sqrt of x^2+y^2+z^2),
angles (atan2), Gaussian shells (exp(-d^2/w^2)), a layered-sine "plasma"
interference field, and the Bessel rings. Pure geometry -> light.

================================================================================
TO WRITE YOUR OWN: copy this file's shape —
  imports  ->  class MyFx(Element): __init__ (precompute geometry) + apply(ctx,out)
           ->  KNOBS  ->  TRIGGERS  ->  build(engine).
================================================================================
"""

from __future__ import annotations

import math  # the stdlib maths library — used heavily below (tau, sin, cos, exp, ...)

import numpy as np

# --- the engine toolkit (these `from ..` imports are what your plugin pulls in) ---
from ..patterns import hsv_to_rgb
from ..visuals.engine import elements as el  # the ready-made library (used by the pads)
from ..visuals.engine.context import Context, EnvFollower, lfo
from ..visuals.engine.element import Element, Knob, Trigger, blend_into

# Bonus maths library. scipy is part of the engine, but importing defensively means
# the plugin never fails to LOAD if it's somehow absent — a good habit to copy.
try:
    from scipy.special import j0 as _besselj0  # Bessel J0 -> clean concentric rings
    _HAVE_SCIPY = True
except Exception:  # pragma: no cover - scipy is normally present
    _HAVE_SCIPY = False
    _besselj0 = None

TAU = math.tau  # 2*pi — we use real maths constants, not magic numbers


class Atlas(Element):
    """Map the live sound onto the cube's pixels, exercising the whole API.

    ``__init__`` runs ONCE — turn the fixed geometry (model.positions, the masks,
    param, element_id) into per-LED fields so the per-frame maths stays cheap.
    ``apply`` runs EVERY frame — read the audio from ``ctx`` and write colours into
    ``out``, an (N,3) float32 buffer the engine then scales (your 'intensity' knob)
    and clips to [0,1] before it reaches the LEDs / the renderer.
    """

    blend = "add"  # the engine composites this element additively onto the frame

    # ------------------------------------------------------------------ once
    def __init__(self, model) -> None:
        P = model.positions                      # (N,3) — the physical LED coordinates
        half = float(model.cfg.half)             # cube half-size in metres (1.30)
        side = float(model.cfg.side_m)           # full side (2.60)
        self.n = int(model.n)

        # HEIGHT 0(bottom)..1(top) — we apportion the SPECTRUM onto this axis.
        self.hy = np.clip((P[:, 1] + half) / side, 0.0, 1.0).astype(np.float32)
        # Which of the 8 spectrum buckets each LED's height lands in, + the blend
        # to the next one up, so the spectrum reads as a smooth gradient (maths: lerp).
        b = self.hy * 7.0
        self.b0 = np.clip(b.astype(np.int32), 0, 7)           # lower bucket index
        self.b1 = np.clip(self.b0 + 1, 0, 7)                  # upper bucket index
        self.bf = (b - self.b0).astype(np.float32)            # 0..1 fraction between them

        # STEREO split: x<0 is the left channel's half of the cube, x>=0 the right.
        self.isL = P[:, 0] < 0.0

        # RADIUS from centre (distance field) — kicks expand through it; rings use it.
        self.rho = np.sqrt((P ** 2).sum(axis=1)).astype(np.float32)
        self.rmax = float(self.rho.max()) or 1.0

        # ANGLE around the vertical axis 0..1 — the oscilloscope wraps the waveform
        # onto this (maths: atan2 of the z,x plane, normalised by tau).
        self.ang = ((np.arctan2(P[:, 2], P[:, 0]) / TAU) % 1.0).astype(np.float32)

        # Normalised x,y in [-1,1] for the plasma interference field.
        self.nx = (P[:, 0] / half).astype(np.float32)
        self.ny = (P[:, 1] / half).astype(np.float32)

        # Masks & index sets straight from the model (precomputed -> fast indexing).
        self.edge = np.where(model.edge_mask)[0]
        self.cornerL = np.where(model.corner_mask & self.isL)[0]
        self.cornerR = np.where(model.corner_mask & ~self.isL)[0]

        # model.param (0..1 along each run) + model.element_id (which of the 12 edges)
        # drive a structure "play-head": a dot chasing along every edge, phase-offset
        # per run so they don't all march in lockstep.
        self.param = model.param.astype(np.float32)
        self.run_phase = ((model.element_id.astype(np.float32) * 0.1318) % 1.0).astype(np.float32)

        # Envelopes: snappy attack, smooth release — for the transient events.
        self.env_kick = EnvFollower(0.45)        # one shockwave per kick onset
        self.env_bL = EnvFollower(0.16)          # left-corner bass
        self.env_bR = EnvFollower(0.16)          # right-corner bass
        self._rng = np.random.default_rng(7)     # deterministic sparkle

        # Reusable scratch colour (avoids per-frame allocation churn).
        self._white = np.array([1.0, 0.85, 0.6], np.float32)

    # tiny helper: read an 8-bucket spectrum at every LED's height (linear blend).
    def _spectrum_at_height(self, buckets) -> np.ndarray:
        bk = np.asarray(buckets, np.float32) if buckets is not None else np.zeros(8, np.float32)
        return bk[self.b0] * (1.0 - self.bf) + bk[self.b1] * self.bf      # -> (N,)

    # ----------------------------------------------------------------- frame
    def apply(self, ctx: Context, out: np.ndarray) -> None:
        f = ctx.features
        t = ctx.t
        sat = ctx.sat(0.95)          # honours the CAPTURE / mono button
        hue0 = ctx.evo_hue           # your 'palette' knob + the engine's slow drift
        size = max(0.15, ctx.size)   # your 'depth' knob

        # ===== 1) THE SPATIAL SPECTRUM — bass low, treble high, L|R across x ========
        # Interpolate each channel's 8-bucket spectrum across HEIGHT, then pick the
        # value for each LED's side. Hue climbs with height (red base -> violet top).
        specL = self._spectrum_at_height(f.buckets_l)        # (N,) left spectrum by height
        specR = self._spectrum_at_height(f.buckets_r)        # (N,) right spectrum by height
        spec = np.where(self.isL, specL, specR).astype(np.float32)
        spec *= 0.75 + 0.6 * ctx.energy                      # ctx.energy: lift with loudness
        hue = (hue0 + 0.66 * self.hy) % 1.0                  # (N,) hue ramp up the cube
        out += hsv_to_rgb(hue, sat, np.clip(spec * 1.25, 0.0, 1.0))   # vectorised -> (N,3)

        # ===== 2) BASS IN THE CORNERS — per channel, snappy (EnvFollower) ===========
        self.env_bL.trigger(float(f.bass_l)); self.env_bR.trigger(float(f.bass_r))
        vL = self.env_bL.step(ctx.dt); vR = self.env_bR.step(ctx.dt)
        warm = (hue0 + 0.02) % 1.0
        # blend_into() is the explicit compositor; scalar v -> a 3-vector, broadcast.
        blend_into(out, self.cornerL, hsv_to_rgb(warm, sat, vL), "add")
        blend_into(out, self.cornerR, hsv_to_rgb(warm, sat, vR), "add")

        # ===== 3) KICKS -> a SHOCKWAVE expanding from the centre (ctx.events) ========
        for e in ctx.events("kick"):
            self.env_kick.trigger(getattr(e, "strength", 1.0))   # each onset re-arms it
        kv = self.env_kick.step(ctx.dt)
        if kv > 0.01:
            # A Gaussian SHELL whose radius grows as the envelope decays (maths: exp).
            grow = (1.0 - kv) * self.rmax * 1.15                 # 0 (just fired) -> outward
            d = np.abs(self.rho - grow)
            shell = np.exp(-(d / (0.10 * self.rmax)) ** 2) * kv
            out += shell[:, None] * self._white

        # ===== 4) WAVEFORM OSCILLOSCOPE wrapped round the vertical axis (.wave) ======
        if f.wave is not None and len(f.wave):
            w = np.asarray(f.wave, np.float32)                   # (m,2) stereo, ~[-1,1]
            m = w.shape[0]
            idx = np.clip((self.ang * (m - 1)).astype(np.int32), 0, m - 1)   # angle->sample
            amp = np.where(self.isL, w[idx, 0], w[idx, 1])       # L on the left, R on the right
            scope = np.clip(np.abs(amp) * 1.4 * size, 0.0, 1.0).astype(np.float32)
            ce = (hue0 + 0.5) % 1.0                              # complementary hue
            out[self.edge] += hsv_to_rgb(ce, sat, scope[self.edge])

        # ===== 5) MID -> a PLASMA interference field (pure maths) ===================
        # Layered sines = a classic demoscene plasma. Phase animates with t; the
        # spatial frequency opens up with the 'depth' knob; amplitude rides the mid band.
        k = 3.0 + 5.0 * size
        plasma = (np.sin(self.nx * k + t * 1.3)
                  + np.sin(self.ny * k * 1.1 - t)
                  + np.sin((self.nx + self.ny) * k * 0.7 + math.sin(t * 0.5) * 2.0))
        plasma = np.clip(0.5 + 0.18 * plasma, 0.0, 1.0) * float(f.mid) * 0.6
        out += hsv_to_rgb((hue0 + 0.33) % 1.0, sat * 0.7, plasma)

        # ===== 6) TREBLE -> sparkle on random edge LEDs (rate rides ctx.density) ====
        if f.treble > 0.05:
            rate = 0.06 * float(f.treble) * (0.6 + ctx.density)   # busier mix -> more sparkle
            spk = (self._rng.random(self.edge.size) < rate).astype(np.float32)
            out[self.edge] += spk[:, None] * np.array([0.9, 0.95, 1.0], np.float32) * float(f.treble)

        # ===== 7) BEAT + LEVEL + BASS -> a breathing floor (lfo + maths) ============
        # A gentle global glow: breathes on the beat phase (lfo), lifts with overall
        # loudness, and gets a low-end push from the mono bass band.
        breathe = lfo("sine", ctx.beat) * 0.09 + 0.04 * float(f.level) + 0.05 * float(f.bass)
        out += breathe

        # ===== 8) STRUCTURE PLAY-HEAD along every edge (model.param + element_id) ====
        # A bright dot chases along each run; phase offset per run via element_id.
        ph = (self.run_phase + t * 0.25) % 1.0
        dd = np.abs(((self.param - ph + 0.5) % 1.0) - 0.5)       # wrapped distance to the head
        head = np.exp(-(dd / 0.045) ** 2) * 0.5                   # maths: Gaussian dot
        hc = np.asarray(hsv_to_rgb((hue0 + 0.12) % 1.0, sat, 1.0), np.float32)
        out[self.edge] += head[self.edge][:, None] * hc

        # ===== 9) BONUS: a Bessel "cymatic" ring if scipy is here (else a cos ring) ==
        # j0(k*rho) draws clean concentric rings; we ride them on the treble. The
        # numpy fallback keeps the plugin working even without scipy.
        ring_amp = 0.10 * float(f.treble)
        if ring_amp > 0.004:
            kr = 6.0 + 10.0 * float(f.mid)
            r = self.rho / self.rmax
            ring = _besselj0(kr * r) if _HAVE_SCIPY else np.cos(kr * r) / (1.0 + self.rho)
            out += np.clip(ring, 0.0, 1.0)[:, None] * np.array([0.4, 0.7, 1.0], np.float32) * ring_amp


# --- the F1 performance surface ------------------------------------------------
# KNOBS map to the four engine-wide effects (KNOB_EFFECTS): 'intensity' scales the
# whole frame, 'hue' feeds ctx.evo_hue, 'speed' sets the hue-drift rate, 'space'
# feeds ctx.size. An element reads the *result* (evo_hue / size), not the raw knob.
KNOBS = [
    Knob("spectrum", "intensity", 0.7),   # overall brightness
    Knob("palette", "hue", 0.0),          # base hue of the whole map
    Knob("motion", "speed", 0.4),         # how fast the palette drifts
    Knob("depth", "space", 0.5),          # spatial spread of scope / plasma / chase
]

# TRIGGERS are arbitrary factories: each pad spawns a transient library Element on
# press. ``make(model, strength, colour) -> Element``; ``hold=True`` sustains it
# until the pad is released. This is how a pad can "do anything that draws".
TRIGGERS = [
    Trigger("pulse", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.3)),
    Trigger("boom", (120, 170, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.5 * s)),
    Trigger("spark", (255, 230, 160), lambda m, s, c: el.SparkBurst(m, c, count=44, release=0.7)),
    Trigger("glow", (255, 150, 90), lambda m, s, c: el.HeldGlow(m, c, attack=0.4, release=1.0), hold=True),
]


def build(engine) -> None:
    """A preset is just "add element(s) to the engine". Here our one teaching
    element does the whole job — but you could ``engine.add(...)`` any mix of the
    library elements (section E above) alongside or instead of it."""
    engine.add(Atlas(engine.model))
