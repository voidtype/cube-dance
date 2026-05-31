"""Placeholder, non-audio test pattern for Phase 0.

This exists only to validate density, addressing, and the buffer -> render
pipeline before audio arrives. It is intentionally simple and is REPLACED in
Phase 1 by audio-driven output that writes the same ``model.colors`` buffer.

Edges get a flowing rainbow sweep (uses ``param`` to travel along each edge);
corners get a brightness pulse (breathing), so the two structural groups read
as visibly distinct behaviour.
"""

from __future__ import annotations

import numpy as np

from .led_topology import CubeModel


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorised HSV -> RGB. Inputs in [0, 1]; returns ``(..., 3)`` in [0, 1]."""
    h = (h % 1.0) * 6.0
    i = np.floor(h).astype(np.int64) % 6
    f = h - np.floor(h)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


class PlaceholderPattern:
    """Time-based scaffold pattern. Call :meth:`apply` once per frame."""

    edge_hue_speed = 0.10  # hue cycles/sec along edges
    edge_band_freq = 2.0  # spatial bands per edge
    edge_band_speed = 0.5  # band travel speed
    corner_pulse_hz = 0.5  # corner breathing rate

    def apply(self, model: CubeModel, t: float) -> None:
        """Write the placeholder colors into ``model.colors`` for time ``t``."""
        colors = model.colors

        # --- Edges: flowing rainbow with a travelling brightness band ---
        e = model.edge_mask
        ep = model.param[e]
        hue = (ep + t * self.edge_hue_speed) % 1.0
        band = 0.55 + 0.45 * np.sin(
            2.0 * np.pi * (ep * self.edge_band_freq - t * self.edge_band_speed)
        )
        ones = np.ones_like(ep)
        colors[e] = hsv_to_rgb(hue, ones, ones) * band[:, None]

        # --- Corners: per-corner brightness pulse (breathing) ---
        c = model.corner_mask
        cid = model.element_id[c].astype(np.float32)
        phase = cid * (np.pi / 4.0)
        pulse = 0.12 + 0.88 * (0.5 + 0.5 * np.sin(2.0 * np.pi * self.corner_pulse_hz * t + phase))
        chue = (cid / 8.0 + t * 0.05) % 1.0
        sat = np.full_like(cid, 0.55)
        colors[c] = hsv_to_rgb(chue, sat, pulse)

        np.clip(colors, 0.0, 1.0, out=colors)
