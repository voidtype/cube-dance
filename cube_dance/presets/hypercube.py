"""`hypercube` - a 4-D tesseract rotating in 4-D and projected 4-D->3-D, a hypercube
morphing inside the truss cube. The 4-D rotation planes (XW/YW/ZW) are driven by the
audio, so the music tumbles it through the fourth dimension.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.75),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.25)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.4 * s)),
    Trigger("comet", (160, 255, 255), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3 * s)),
    Trigger("glint", (200, 220, 255), lambda m, s, c: el.SparkBurst(m, c, count=26, release=0.6)),
]


def build(engine) -> None:
    engine.add(fx.Tesseract(engine.model, hue=0.6))
