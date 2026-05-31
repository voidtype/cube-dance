"""Base class for visual elements + the performance control schema.

An element writes its contribution into the shared `(N,3)` buffer over a region
with a blend mode. Subclasses implement ``apply(ctx, out)``.

A preset also declares its **performance schema**: ``KNOBS`` (the focused deck's
4 knob params) and ``TRIGGERS`` (the deck's pad cells). A trigger is an *arbitrary
preset function* that, when a pad is hit, spawns a transient element on the deck
(a stab, strobe, riser, burst, ... whatever the preset wants) -- so the pads are
fully preset-defined, with a colour annotation each.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

# The four per-deck knob effects (fixed slots; presets relabel + set defaults).
KNOB_EFFECTS = ("intensity", "hue", "speed", "space")


@dataclass
class Knob:
    """One knob param for a deck: a label, which effect it drives, a default."""

    label: str
    effect: str = "intensity"  # one of KNOB_EFFECTS
    default: float = 0.5


@dataclass
class Trigger:
    """One pad cell: a label, a colour annotation, and a factory.

    ``make(model, strength, color)`` returns a transient :class:`Element` that the
    engine composites until it reports ``done``. The factory is arbitrary preset
    code, so a trigger can do anything that draws into the buffer.
    """

    label: str
    color: tuple[int, int, int]
    make: Callable[..., "Element"]


def blend_into(out: np.ndarray, idx, rgb, mode: str = "add") -> None:
    """Composite ``rgb`` into ``out[idx]`` with the given blend mode."""
    if idx is None:
        sub = out
    else:
        sub = out[idx]
    if mode == "max":
        result = np.maximum(sub, rgb)
    else:  # add
        result = sub + rgb
    if idx is None:
        out[:] = result
    else:
        out[idx] = result


def blend_into(out: np.ndarray, idx, rgb, mode: str = "add") -> None:
    """Composite ``rgb`` into ``out[idx]`` with the given blend mode."""
    if idx is None:
        sub = out
    else:
        sub = out[idx]
    if mode == "max":
        result = np.maximum(sub, rgb)
    else:  # add
        result = sub + rgb
    if idx is None:
        out[:] = result
    else:
        out[idx] = result


class Element:
    blend = "add"
    done = False  # transient elements set this True when finished (engine prunes them)

    def apply(self, ctx, out: np.ndarray) -> None:  # pragma: no cover - interface
        raise NotImplementedError
