"""`matrix` — digital rain. Bright green heads fall down the cube with fading
trails, density rising with the treble. The 'fall' knob sets the speed, 'tint'
recolours the streams. Sparse, downward, techy — the opposite of a warm wash.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    ColorStab, DigitalRain, Pulse, RiserSweep, SparkBurst, StrobeBurst,
)

KNOBS = [
    Knob("density", "intensity", 0.65),
    Knob("tint", "hue", 0.0),
    Knob("drift", "speed", 0.12),
    Knob("fall", "space", 0.5),
]

TRIGGERS = [
    Trigger("glitch", (120, 255, 140), lambda m, s, c: SparkBurst(m, c, count=54, release=0.4)),
    Trigger("drop", (180, 255, 200), lambda m, s, c: ColorStab(m, c, gain=s, release=0.3, region="beams")),
    Trigger("flash", (255, 255, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.2, flashes=4)),
    Trigger("wipe", (60, 255, 120), lambda m, s, c: RiserSweep(m, c, dur=1.0, gain=0.9 * s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(Pulse(m, hue=0.34, sat=0.85, base=0.02, gain=0.12, react="energy"))
    engine.add(DigitalRain(m, hue_base=0.34, sat=0.9, drops=6, trail=0.22))
