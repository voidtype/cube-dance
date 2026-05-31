"""Hardware-agnostic Traktor F1 control state.

Written by either the virtual on-screen panel or MIDI input; read by the mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Function buttons (top two rows on the F1). Order matters for the panel layout.
BUTTONS: tuple[str, ...] = (
    "SYNC", "QUANT", "CAPTURE",
    "SHIFT", "REVERSE", "TYPE", "SIZE", "BROWSE",
)


@dataclass
class ControlState:
    knobs: list[float] = field(default_factory=lambda: [0.5, 0.5, 0.5, 0.5])  # FILTER 1-4
    faders: list[float] = field(default_factory=lambda: [0.85, 0.4, 0.3, 0.05])
    buttons: dict[str, bool] = field(default_factory=lambda: {b: False for b in BUTTONS})
    p: int = 0  # 2-digit display value 0..99
    pads: list[bool] = field(default_factory=lambda: [False] * 16)
    # A pad hit fires a decaying full-cube colour flash (a manual accent / strobe).
    flash_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    flash_level: float = 0.0

    def step_encoder(self, delta: int) -> None:
        self.p = (self.p + int(delta)) % 100

    def toggle(self, name: str) -> None:
        if name in self.buttons:
            self.buttons[name] = not self.buttons[name]
