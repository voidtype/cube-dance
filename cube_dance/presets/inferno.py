"""`inferno` — the cube is on fire. A flickering warm blaze, hottest at the base,
embers licking up, surging with the bass. Locked warm palette (hue knob tints it).
Nothing like the spectrum visuals.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine.elements import (
    ColorStab, HeatField, KickPulse, Pulse, RiserSweep, SparkBurst,
)

KNOBS = [
    Knob("heat", "intensity", 0.7),
    Knob("tint", "hue", 0.0),
    Knob("ember", "speed", 0.2),
    Knob("reach", "space", 0.55),
]

TRIGGERS = [
    Trigger("flare", (255, 120, 20), lambda m, s, c: RiserSweep(m, c, dur=1.0, gain=1.2 * s)),
    Trigger("fireball", (255, 70, 20), lambda m, s, c: ColorStab(m, c, gain=1.2 * s, release=0.3)),
    Trigger("embers", (255, 180, 60), lambda m, s, c: SparkBurst(m, c, count=44, release=0.8)),
    Trigger("roar", (255, 40, 0), lambda m, s, c: ColorStab(m, c, gain=1.4 * s, release=0.5, region="corners")),
]


def build(engine) -> None:
    m = engine.model
    engine.add(HeatField(m, gain=1.15))
    engine.add(Pulse(m, hue=0.02, sat=0.95, base=0.03, gain=0.35, react="bass"))
    engine.add(KickPulse(m, region="corners", hue=0.05, sat=0.9, gain=0.7, release=0.18))
