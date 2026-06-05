"""`mandelbox` - escape-time of the Mandelbox (a 3-D Mandelbrot cousin), navigated
by the full spectrum: bass folds it, treble sets the min-radius, energy zooms, mids
rotate - so the music flies you through the fractal.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import effects as fx, elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("zoom", "space", 0.5),
]

TRIGGERS = [
    Trigger("dive", (120, 160, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.5 * s)),
    Trigger("stab", (255, 120, 220), lambda m, s, c: el.ColorStab(m, c, gain=s, release=0.28)),
    Trigger("comet", (160, 255, 220), lambda m, s, c: el.Comet(m, c, dur=0.9, turns=1.5, gain=1.3 * s)),
    Trigger("confetti", (220, 160, 255), lambda m, s, c: el.Confetti(m, count=90, release=0.55)),
]


def build(engine) -> None:
    engine.add(fx.Mandelbox(engine.model, hue=0.62))
