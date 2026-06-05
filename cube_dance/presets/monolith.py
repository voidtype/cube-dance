"""`monolith` - a heavy, imposing peak presence: deep bass body, anchored corners, a slow orbiting band."""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import elements as el

KNOBS = [
    Knob("drive", "intensity", 0.78),
    Knob("colour", "hue", 0.0),
    Knob("evolve", "speed", 0.3),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    Trigger("slam", (255, 255, 255), lambda m, s, c: el.ColorStab(m, c, gain=1.3 * s, release=0.16)),
    Trigger("shock", (120, 160, 255), lambda m, s, c: el.Shockwave(m, c, dur=0.6, gain=1.5 * s)),
    Trigger("riser", (255, 120, 40), lambda m, s, c: el.RiserSweep(m, c, dur=1.0, gain=1.1 * s)),
    Trigger("strobe", (200, 220, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.06), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(el.Pulse(m, hue=0.0, sat=0.9, base=0.05, gain=0.5, react="bass"))
    engine.add(el.BassCorners(m, hue=0.02, sat=1.0))
    engine.add(el.Sweep(m, axis=1, rate=0.08, width=0.16, hue=0.6, gain=0.5))
    engine.add(el.KickPulse(m, region="corners", sat=0.0, gain=0.9, release=0.18))
