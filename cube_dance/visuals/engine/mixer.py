"""A 4-deck preset mixer: several preset engines blended by per-deck volume.

Each deck is an independent ``VisualEngine`` running a preset with its own
evolution state; the decks share one ``VisualParams`` (so the F1 knobs are a
global "feel" across all decks) and are blended additively, each weighted by its
deck volume (the F1 fader). The mixer is a ``Visual`` (``update(model, t, features)``).
"""

from __future__ import annotations

import numpy as np

from ..params import VisualParams
from .engine import VisualEngine


class DeckMixer:
    def __init__(self, model, n_buckets: int = 8, vparams: VisualParams | None = None,
                 deck_presets: list[str] | None = None) -> None:
        from ... import presets  # late import (presets import the elements)

        self.model = model
        self.n_buckets = n_buckets
        self.vparams = vparams or VisualParams()
        order = list(presets.PRESET_ORDER)
        names = list(deck_presets or order[:4])
        # Pad/truncate to exactly 4 decks, cycling the order for any gaps.
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
        # Deck volumes (the faders); only deck 1 audible by default.
        self.volumes: list[float] = [0.85, 0.0, 0.0, 0.0]
        self._scratch = np.zeros((model.n, 3), np.float32)
        self._acc = np.zeros((model.n, 3), np.float32)

    def _make_deck(self, name: str) -> VisualEngine:
        from ... import presets

        eng = VisualEngine(self.model, n_buckets=self.n_buckets, vparams=self.vparams)
        presets.load(name, eng)
        return eng

    def set_deck_preset(self, i: int, name: str) -> None:
        """Swap the preset on deck ``i`` (rebuilds its elements)."""
        from ... import presets

        order = list(presets.PRESET_ORDER)
        self.decks[i] = self._make_deck(name)
        self.preset_name[i] = name
        self.preset_index[i] = order.index(name) if name in order else 0

    def update(self, model, t: float, features) -> None:
        acc = self._acc
        acc[:] = 0.0
        for i, deck in enumerate(self.decks):
            v = float(self.volumes[i]) if i < len(self.volumes) else 0.0
            if v <= 0.005:
                continue  # muted deck: skip the composite (its state simply pauses)
            deck.render(model, t, features, self._scratch)
            acc += self._scratch * v
        if self.vparams.master != 1.0:
            acc *= self.vparams.master
        np.clip(acc, 0.0, 1.0, out=model.colors)
