"""`inferno` — the cube is on fire. A flickering warm blaze, hottest at the base,
embers licking up, surging with the bass. Locked warm palette (hue knob tints it).

Pads (fire): rising embers, a fireball shockwave, a flame flare, a heat wipe up.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    HeatField, KickPulse, Pulse, RiserSweep, Shockwave, SparkBurst, Wipe,
)

KNOBS = [
    Knob("heat", "intensity", 0.7),
    Knob("tint", "hue", 0.0),
    Knob("ember", "speed", 0.2),
    Knob("reach", "space", 0.55),
]

TRIGGERS = [
    Trigger("embers", (255, 180, 60), lambda m, s, c: SparkBurst(m, c, count=50, release=0.8)),
    Trigger("fireball", (255, 70, 20), lambda m, s, c: Shockwave(m, c, dur=0.6, gain=1.5 * s)),
    Trigger("flare", (255, 120, 20), lambda m, s, c: RiserSweep(m, c, dur=1.0, gain=1.2 * s)),
    Trigger("heatwipe", (255, 40, 0), lambda m, s, c: Wipe(m, c, axis=1, dur=0.9, gain=1.1 * s)),
]


def build(engine) -> None:
    m = engine.model
    engine.add(HeatField(m, gain=1.15))
    engine.add(Pulse(m, hue=0.02, sat=0.95, base=0.03, gain=0.35, react="bass"))
    engine.add(KickPulse(m, region="corners", hue=0.05, sat=0.9, gain=0.7, release=0.18))
