"""The visual engine: composites elements, evolves, and hosts the deck's
performance controls (knob params + pad triggers that spawn transient elements)."""

from __future__ import annotations

import math

import numpy as np

from ..params import VisualParams
from . import elements as E
from .context import Context
from .element import Knob, Trigger

# Default performance schema if a preset declares none.
DEFAULT_KNOBS = (
    Knob("intensity", "intensity", 0.6),
    Knob("colour", "hue", 0.5),
    Knob("evolve", "speed", 0.4),
    Knob("space", "space", 0.5),
)
_FALLBACK = {"intensity": 0.6, "hue": 0.0, "speed": 0.4, "space": 0.5}


def default_triggers() -> list[Trigger]:
    return [
        Trigger("flash", (255, 255, 255), lambda m, s, c: E.ColorStab(m, c, gain=s, release=0.3)),
        Trigger("strobe", (120, 180, 255), lambda m, s, c: E.StrobeBurst(m, c, gain=1.3)),
        Trigger("riser", (255, 150, 40), lambda m, s, c: E.RiserSweep(m, c, gain=1.0)),
        Trigger("spark", (120, 255, 160), lambda m, s, c: E.SparkBurst(m, c, count=40)),
    ]


class VisualEngine:
    """A `Visual` (``update(model, t, features)``) that runs composable elements.

    Holds a smoothed energy + onset density (composition awareness), an accelerating
    global hue (evolution), the deck's **knob params** and **pad triggers**, plus a
    list of **transient** elements (spawned by triggers) that self-expire.
    """

    def __init__(self, model, n_buckets: int = 8, vparams: VisualParams | None = None) -> None:
        self.model = model
        self.n_buckets = n_buckets
        self.vparams = vparams or VisualParams()
        self.elements: list = []
        self.transients: list = []
        self._last_t: float | None = None
        self._energy = 0.0
        self._density = 0.0
        self._hue = 0.0
        self._elapsed = 0.0
        self.params = dict(_FALLBACK)
        self.set_schema()  # default knobs + triggers

    # --- Composition ---------------------------------------------------------
    def add(self, element):
        self.elements.append(element)
        return element

    # --- Performance schema (set by the loaded preset) -----------------------
    def set_schema(self, knob_spec=None, triggers=None) -> None:
        self.knob_spec: list[Knob] = list(knob_spec) if knob_spec else list(DEFAULT_KNOBS)
        self.knob_vals: list[float] = [kb.default for kb in self.knob_spec]
        trs = list(triggers) if triggers else default_triggers()
        self.triggers: dict[str, Trigger] = {t.label: t for t in trs}
        self.trigger_order: list[str] = [t.label for t in trs]
        self._apply_knobs()

    def fire(self, label: str, strength: float = 1.0):
        tr = self.triggers.get(label)
        if tr is None:
            return None
        el = tr.make(self.model, float(strength), tuple(c / 255.0 for c in tr.color))
        if el is not None:
            self.transients.append(el)
        return el  # so a hold trigger's owner can .release() it later

    def _apply_knobs(self) -> None:
        p = dict(_FALLBACK)
        for i, kb in enumerate(self.knob_spec):
            if i < len(self.knob_vals):
                p[kb.effect] = float(self.knob_vals[i])
        self.params = p

    # --- Frame ---------------------------------------------------------------
    def render(self, model, t: float, features, out: np.ndarray) -> None:
        """Composite elements + transients into ``out`` (caller owns master + clip)."""
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t
        self._elapsed += dt
        self._apply_knobs()
        p = self.params
        vp = self.vparams

        level = float(getattr(features, "level", 0.0) or 0.0)
        n_events = len(getattr(features, "events", None) or [])
        if dt > 0:
            self._energy += (level - self._energy) * (1.0 - math.exp(-dt / 0.6))
            self._density += ((n_events / dt) - self._density) * (1.0 - math.exp(-dt / 1.0))

        # Evolution: accelerating hue drift, scaled by the per-deck speed knob.
        if dt > 0 and not vp.freeze:
            rate = (vp.hue_drift_base
                    * (1.0 + (self._elapsed / 60.0) * vp.hue_accel_per_min)
                    * (0.5 + self._energy) * (2.5 * p["speed"]))
            if vp.reverse:
                rate = -rate
            self._hue = (self._hue + rate * dt) % 1.0
        evo_hue = (self._hue + p["hue"]) % 1.0
        size = (0.5 + 1.3 * p["space"]) * (1.4 if vp.size_boost else 1.0)

        ctx = Context(model=model, t=t, dt=dt, features=features, evo_hue=evo_hue,
                      energy=min(1.0, self._energy * 1.3), density=self._density,
                      size=size, mono=vp.mono)

        out[:] = 0.0
        for el in self.elements:
            el.apply(ctx, out)
        if self.transients:
            for el in self.transients:
                el.apply(ctx, out)
            self.transients = [e for e in self.transients if not e.done]

        gain = 0.2 + 1.4 * p["intensity"]
        if gain != 1.0:
            out *= gain

    def update(self, model, t: float, features) -> None:
        """Standalone path: render into the model buffer, apply master, clip."""
        out = model.colors
        self.render(model, t, features, out)
        if self.vparams.master != 1.0:
            out *= self.vparams.master
        np.clip(out, 0.0, 1.0, out=out)
