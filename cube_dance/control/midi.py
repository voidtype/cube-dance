"""Basic Traktor F1 MIDI input (optional, guarded).

Opens the first F1-looking input port on a background thread and feeds the shared
ControlState (CC -> knobs/faders, notes -> button toggles). If mido / a backend /
the hardware is absent it is a silent no-op. Exact CC/note numbers vary by the
Controller-Editor mapping; sensible defaults are used now and will be made
configurable in Phase 5.
"""

from __future__ import annotations

import threading

from .state import BUTTONS, ControlState


class MidiInput:
    def __init__(self, state: ControlState) -> None:
        self.state = state
        self._port = None
        self._stop = False
        self.active = False

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:  # pragma: no cover - needs hardware
        try:
            import mido

            names = mido.get_input_names()
            name = next((n for n in names if any(k in n for k in ("Traktor", "Kontrol", "F1"))), None)
            if name is None:
                return
            self._port = mido.open_input(name)
            self.active = True
            for msg in self._port:
                if self._stop:
                    break
                self._handle(msg)
        except Exception:
            self.active = False

    def _handle(self, msg) -> None:  # pragma: no cover - needs hardware
        s = self.state
        if msg.type == "control_change":
            v = msg.value / 127.0
            cc = msg.control
            if 0 <= cc < 4:
                s.knobs[cc] = v
            elif 4 <= cc < 8:
                s.faders[cc - 4] = v
        elif msg.type == "note_on" and msg.velocity > 0:
            i = msg.note % len(BUTTONS)
            s.toggle(BUTTONS[i])

    def close(self) -> None:  # pragma: no cover - needs hardware
        self._stop = True
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
                pass
