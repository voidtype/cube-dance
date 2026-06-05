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
    # Faders are per-deck volumes (Phase 5): deck 1 up, the rest silent at launch.
    faders: list[float] = field(default_factory=lambda: [0.85, 0.0, 0.0, 0.0])
    buttons: dict[str, bool] = field(default_factory=lambda: {b: False for b in BUTTONS})
    p: int = 0  # 2-digit display value (Phase 5: the focused deck's preset index)
    p_mod: int = 100  # encoder wrap (the app sets this to the preset count so it wraps cleanly)
    focus_deck: int = 0  # selected channel/deck (bottom-row button or fader touch)
    pads: list[bool] = field(default_factory=lambda: [False] * 16)
    pad_glow: list[float] = field(default_factory=lambda: [0.0] * 16)  # UI glow per pad
    # Pad hits queue (col, row) presses/releases for the app to fire as preset triggers.
    pad_queue: list[tuple[int, int]] = field(default_factory=list)
    pad_release: list[tuple[int, int]] = field(default_factory=list)  # for hold triggers

    def step_encoder(self, delta: int) -> None:
        self.p = (self.p + int(delta)) % max(1, self.p_mod)

    def toggle(self, name: str) -> None:
        if name in self.buttons:
            self.buttons[name] = not self.buttons[name]

    def press_pad(self, col: int, row: int) -> None:
        self.pad_queue.append((col, row))
        i = row * 4 + col
        if 0 <= i < 16:
            self.pad_glow[i] = 1.0

    def release_pad(self, col: int, row: int) -> None:
        self.pad_release.append((col, row))
