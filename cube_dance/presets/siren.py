"""`siren` — emergency/rave alarm. The left and right halves of the cube hard-cut
between two colours (red/blue by default) on a fast pulse, kicks punch white.
The 'rate' knob sets the alternation speed, 'colours' shifts both hues. Stark,
alarming, and binary — nothing subtle about it.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import ColorStab, KickPulse, RiserSweep, SirenStrobe, StrobeBurst

KNOBS = [
    Knob("intensity", "intensity", 0.7),
    Knob("colours", "hue", 0.0),
    Knob("drift", "speed", 0.3),
    Knob("rate", "space", 0.5),
]

TRIGGERS = [
    Trigger("blip", (255, 255, 255), lambda m, s, c: StrobeBurst(m, c, gain=1.5, flashes=6, interval=0.05)),
    Trigger("red", (255, 30, 30), lambda m, s, c: ColorStab(m, c, gain=1.3 * s, release=0.2)),
    Trigger("blue", (40, 80, 255), lambda m, s, c: ColorStab(m, c, gain=1.3 * s, release=0.2)),
    Trigger("riser", (255, 200, 0), lambda m, s, c: RiserSweep(m, c, dur=0.8, gain=1.2 * s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(SirenStrobe(m, hue_a=0.0, hue_b=0.62, sat=1.0, rate=3.0))
    engine.add(KickPulse(m, region="all", sat=0.0, gain=0.8, release=0.10))
