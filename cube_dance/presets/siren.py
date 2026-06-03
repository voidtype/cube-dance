"""`siren` — emergency/rave alarm. The left and right halves of the cube hard-cut
between two colours (red/blue by default) on a fast pulse, kicks punch white.
The 'rate' knob sets the alternation speed, 'colours' shifts both hues.

Pads (alarm): a red stab, a blue stab, a white strobe, a shockwave.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import ColorStab, KickPulse, Shockwave, SirenStrobe, StrobeBurst

KNOBS = [
    Knob("intensity", "intensity", 0.7),
    Knob("colours", "hue", 0.0),
    Knob("drift", "speed", 0.3),
    Knob("rate", "space", 0.5),
]

TRIGGERS = [
    Trigger("red", (255, 30, 30), lambda m, s, c: ColorStab(m, c, gain=1.3 * s, release=0.18)),
    Trigger("blue", (40, 80, 255), lambda m, s, c: ColorStab(m, c, gain=1.3 * s, release=0.18)),
    Trigger("strobe", (255, 255, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.5, flashes=6, interval=0.05)),
    Trigger("shock", (255, 200, 0), lambda m, s, c: Shockwave(m, c, dur=0.5, gain=1.5 * s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(SirenStrobe(m, hue_a=0.0, hue_b=0.62, sat=1.0, rate=3.0))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=0.8, release=0.10))
