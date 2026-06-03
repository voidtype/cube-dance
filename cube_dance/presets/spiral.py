"""`spiral` — a 3-D double helix wraps the cube. LEDs light where the spiral
intersects the wireframe, and the crossings of the two counter-rotating helices
glow white (the intersection of the two spirals). Orbit it in the viewer; the
'coils' knob sets tightness, rotation accelerates with energy, kicks bloom it.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import ColorStab, Comet, Pulse, Shockwave, SparkBurst, Spiral

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("density", "space", 0.8),  # 0 -> 100% : how much of the helix has grown in
]

TRIGGERS = [
    Trigger("flash", (255, 255, 255), lambda m, s, c: ColorStab(m, c, gain=s, release=0.25)),
    Trigger("shock", (120, 200, 255), lambda m, s, c: Shockwave(m, c, dur=0.7, gain=1.3 * s)),
    Trigger("comet", (255, 150, 40), lambda m, s, c: Comet(m, c, dur=1.0, turns=1.5, gain=1.2 * s)),
    Trigger("glint", (200, 255, 220), lambda m, s, c: SparkBurst(m, c, count=26, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(Pulse(m, hue=0.5, sat=0.6, base=0.02, gain=0.14, react="energy"))
    engine.add(Spiral(m, radius=1.18, turns=3.0, width=0.14, hue=0.0, hue_b=0.5, double=True))
