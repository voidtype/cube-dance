"""Base class for visual elements.

An element writes its contribution into the shared `(N,3)` buffer over a region
with a blend mode. Subclasses implement ``apply(ctx, out)``.
"""

from __future__ import annotations

import numpy as np


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

    def apply(self, ctx, out: np.ndarray) -> None:  # pragma: no cover - interface
        raise NotImplementedError
