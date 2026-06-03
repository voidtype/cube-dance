"""`vortex` — a black hole. A flat spiral of hard, stark arms rotates around an
empty dark core, reading as a spiral from the front. Rotation accelerates with
energy, arms fatten on the bass; every launch starts in a random orientation.
The 'swirl' knob sets arm tightness. Pads are all about the swirl.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import Comet, Confetti, Lightning, Shockwave, Vortex

KNOBS = [
    Knob("bright", "intensity", 0.75),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("swirl", "space", 0.5),
]

TRIGGERS = [
    Trigger("blast", (255, 255, 255), lambda m, s, c: Shockwave(m, c, dur=0.6, gain=1.5 * s)),
    Trigger("comet", (120, 220, 255), lambda m, s, c: Comet(m, c, dur=0.8, turns=2.0, gain=1.4 * s)),
    Trigger("bolt", (200, 160, 255), lambda m, s, c: Lightning(m, c, strikes=4, gain=1.6)),
    Trigger("confetti", (255, 120, 200), lambda m, s, c: Confetti(m, count=90, release=0.6)),
]


def build(engine) -> None:
    m = engine.model
    # Just the vortex: stark single-hue arms over true black (no wash) = black hole.
    engine.add(Vortex(m, arms=3, twist=2.8, hue=0.6, sat=1.0, axis=2, duty=0.32, core=0.18))
