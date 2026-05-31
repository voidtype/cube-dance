"""Map the F1 control state onto the global visual flags (Phase 5).

The performance surface is split:
- **Faders** = per-deck volumes (read by the mixer).
- **Knobs** = the focused deck's preset params (routed by the app to that deck).
- **Pads** = the focused/per-column deck's preset triggers (routed by the app).
- **Browse encoder** = the selected deck's preset (handled by the app).
- **Function buttons** = the global flags set here.
"""

from __future__ import annotations

from .state import ControlState

# Fallback labels (presets override the knob labels live; faders show deck names).
KNOB_ROLES = ("intensity", "colour", "evolve", "space")
FADER_ROLES = ("deck 1", "deck 2", "deck 3", "deck 4")

# Function-button -> global flag.
BUTTON_ROLES = {
    "QUANT": "quantise triggers to the beat",
    "TYPE": "mono / stark (white)",
    "SHIFT": "freeze the palette",
    "REVERSE": "reverse colour drift",
    "SYNC": "pulse the rig on the beat",
    "CAPTURE": "blackout (kill)",
    "SIZE": "fatten elements",
    "BROWSE": "reset deck knobs to defaults",
}


class ControlMap:
    def apply(self, s: ControlState, vp, ap=None) -> None:
        b = s.buttons
        vp.mono = bool(b.get("TYPE"))
        vp.freeze = bool(b.get("SHIFT"))
        vp.reverse = bool(b.get("REVERSE"))
        vp.size_boost = bool(b.get("SIZE"))
        vp.sync_pulse = bool(b.get("SYNC"))
        vp.blackout = bool(b.get("CAPTURE"))
