"""A 4-deck preset mixer: several preset engines blended by per-deck volume.

Each deck is an independent ``VisualEngine`` running a preset with its own
evolution state, knob params, and pad triggers; the decks share one
``VisualParams`` (the global button flags) and are blended additively, each
weighted by its deck volume (the F1 fader). The mixer is a ``Visual``.
"""

from __future__ import annotations

import numpy as np

from ..params import VisualParams
from .context import EnvFollower
from .engine import VisualEngine


class DeckMixer:
    def __init__(self, model, n_buckets: int = 8, vparams: VisualParams | None = None,
                 deck_presets: list[str] | None = None) -> None:
        from ... import presets

        self.model = model
        self.n_buckets = n_buckets
        self.vparams = vparams or VisualParams()
        order = list(presets.PRESET_ORDER)
        names = list(deck_presets or order[:4])
        while len(names) < 4:
            names.append(order[len(names) % len(order)])
        self.n_decks = 4
        self.decks: list[VisualEngine] = []
        self.preset_name: list[str] = []
        self.preset_index: list[int] = []
        for name in names[:4]:
            self.decks.append(self._make_deck(name))
            self.preset_name.append(name)
            self.preset_index.append(order.index(name) if name in order else 0)
        self.volumes: list[float] = [0.85, 0.0, 0.0, 0.0]
        self._scratch = np.zeros((model.n, 3), np.float32)
        self._acc = np.zeros((model.n, 3), np.float32)
        self._pulse = EnvFollower(0.18)
        self._last_t: float | None = None

    def _make_deck(self, name: str) -> VisualEngine:
        from ... import presets

        eng = VisualEngine(self.model, n_buckets=self.n_buckets, vparams=self.vparams)
        presets.load(name, eng)
        return eng

    def set_deck_preset(self, i: int, name: str) -> None:
        from ... import presets

        order = list(presets.PRESET_ORDER)
        self.decks[i] = self._make_deck(name)
        self.preset_name[i] = name
        self.preset_index[i] = order.index(name) if name in order else 0

    # --- Performance surface accessors (for the F1 panel + app) --------------
    def fire(self, deck: int, label: str, strength: float = 1.0):
        if 0 <= deck < self.n_decks:
            return self.decks[deck].fire(label, strength)
        return None

    def trigger_hold(self, deck: int, label: str) -> bool:
        tr = self.decks[deck].triggers.get(label) if 0 <= deck < self.n_decks else None
        return bool(tr and tr.hold)

    def trigger_cells(self, deck: int):
        """Up to 4 (label, (r,g,b)) for a deck's pad column (top to bottom)."""
        eng = self.decks[deck]
        return [(lbl, eng.triggers[lbl].color) for lbl in eng.trigger_order[:4]]

    def trigger_label(self, deck: int, row: int):
        eng = self.decks[deck]
        return eng.trigger_order[row] if row < len(eng.trigger_order) else None

    def knob_labels(self, deck: int):
        return [kb.label for kb in self.decks[deck].knob_spec]

    def knob_vals(self, deck: int):
        return list(self.decks[deck].knob_vals)

    def set_knob(self, deck: int, i: int, v: float) -> None:
        eng = self.decks[deck]
        if i < len(eng.knob_vals):
            eng.knob_vals[i] = float(v)

    def reset_knobs(self, deck: int) -> None:
        eng = self.decks[deck]
        eng.knob_vals = [kb.default for kb in eng.knob_spec]

    # --- Frame ---------------------------------------------------------------
    def update(self, model, t: float, features) -> None:
        vp = self.vparams
        dt = 0.0 if self._last_t is None else max(0.0, min(t - self._last_t, 0.1))
        self._last_t = t
        acc = self._acc
        acc[:] = 0.0
        for i, deck in enumerate(self.decks):
            v = float(self.volumes[i]) if i < len(self.volumes) else 0.0
            if v <= 0.005:
                continue  # muted deck: skip the composite (its state simply pauses)
            deck.render(model, t, features, self._scratch)
            acc += self._scratch * v

        if vp.sync_pulse:  # SYNC: pump the whole rig on detected kicks
            for e in (getattr(features, "events", None) or []):
                if e.kind == "kick":
                    self._pulse.trigger(e.strength)
            acc *= (1.0 + 0.55 * self._pulse.step(dt))

        if vp.blackout:  # CAPTURE: kill
            acc *= 0.0
        if vp.master != 1.0:
            acc *= vp.master
        np.clip(acc, 0.0, 1.0, out=model.colors)
