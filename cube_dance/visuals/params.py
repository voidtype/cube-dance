"""Tunable parameters for the cube-aware visual.

A plain dataclass so the Phase-4 DSL / saveable presets can populate it later.
Defaults are chosen to look good out of the box.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisualParams:
    # Stark contrast on top of the AGC's gamma (1.0 = none).
    gamma: float = 1.0
    # Colour evolution: a global hue phase drifts and *accelerates* over a set.
    hue_drift_base: float = 0.015  # cycles/sec at the start
    hue_accel_per_min: float = 0.5  # drift rate grows this fraction each minute
    hue_spread: float = 0.78  # hue range mapped across the frequency buckets (beams)
    # Bass corners.
    corner_hue: float = 0.0  # base warm hue (red)
    corner_hue_drift: float = 0.012  # cycles/sec
    corner_sat: float = 0.95
    # Beams.
    beam_sat: float = 0.9
    # A small always-on floor so the cube never reads fully dead (0 = pure reactive).
    floor: float = 0.0
