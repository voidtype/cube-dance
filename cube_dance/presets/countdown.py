"""`countdown` - the cube counts the crowd into the new year.

Hit the **START** pad at T-10s and the cube runs a 10 -> 1 countdown down the
frame (cool at the top, hot near zero, a flash on every second), then blasts into
the bells with a white burst + rainbow bloom. **BURST** fires the celebration on
its own, for hitting the exact stroke of midnight by hand. Idle, it sits on a
calm "ready" glow.
"""

from __future__ import annotations

from ..visuals.engine.element import Knob, Trigger
from ..visuals.engine import elements as el

KNOBS = [
    Knob("bright", "intensity", 0.7),
    Knob("colour", "hue", 0.08),
    Knob("evolve", "speed", 0.1),
    Knob("size", "space", 0.5),
]

TRIGGERS = [
    # the button: start the ten-second countdown
    Trigger("START", (255, 210, 120), lambda m, s, c: el.Countdown(m, c, dur=10.0)),
    # fire just the celebration (the manual "GO" at midnight)
    Trigger("BURST", (255, 255, 255), lambda m, s, c: el.Countdown(m, c, dur=0.0)),
    # a tension build to hold into the countdown
    Trigger("flare", (255, 150, 60), lambda m, s, c: el.RiserSweep(m, c, dur=1.6, gain=1.0 * s)),
    # a held strobe for the drop
    Trigger("strobe", (200, 220, 255), lambda m, s, c: el.HeldStrobe(m, c, interval=0.06), hold=True),
]


def build(engine) -> None:
    m = engine.model
    engine.add(el.AmbientWash(m, base=0.05, sat=0.5))   # a calm "ready" glow
    engine.add(el.BassCorners(m, hue=0.08, sat=0.9))    # corners breathe with the room
