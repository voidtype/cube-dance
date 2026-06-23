"""Thin glue between the browser and the REAL cube_dance engine.

This file lives only in ``web/`` and imports the engine package *unchanged* — no
edits to ``cube_dance`` anywhere. It runs inside Pyodide (CPython+numpy in WASM).
JS owns the screen, audio and controls; this owns the actual visual engine.

Data exchange is zero-marshalling: Python owns both buffers and JS reads/writes
their Float32Array views each frame (see ``feat`` / ``out``).
"""

from __future__ import annotations

import numpy as np

# --- Pyodide/WASM compatibility shim (glue only — the engine is untouched) ---
# On 32-bit numpy (WASM), np.choose() refuses an int64 index under the 'safe'
# cast rule; the desktop default int is int64, so hsv_to_rgb() (used by every
# element) trips on it. Coerce the index to the platform int. No-op on 64-bit.
if np.intp(0).itemsize < 8:  # pragma: no cover - only true under Pyodide/WASM
    _np_choose = np.choose

    def _safe_choose(a, choices, out=None, mode="raise"):
        return _np_choose(np.asarray(a).astype(np.intp), choices, out=out, mode=mode)

    np.choose = _safe_choose

from cube_dance.hardware.model import build_hardware_model
from cube_dance.visuals.base import Features
from cube_dance.visuals.engine import VisualEngine
from cube_dance import presets

# feat buffer layout (JS writes these each frame; see web/main.js):
#  0 level  1 bass  2 mid  3 treble  4 bass_l  5 bass_r  6 beat  7 kick(0/1)
#  8 kickStrength   9..16 buckets_l[8]   17..24 buckets_r[8]
#  25 .. 25+M-1  waveform L   25+M .. 25+2M-1  waveform R   (the scope; M=_WAVE_M)
_WAVE_M = 96  # downsampled oscilloscope samples per channel (fed by the web glue)
_F = 25 + 2 * _WAVE_M


class _Ev:  # the minimal onset event the engine reads (.kind / .strength)
    __slots__ = ("kind", "strength")

    def __init__(self, kind: str, strength: float = 1.0) -> None:
        self.kind = kind
        self.strength = float(strength)


class Bridge:
    def __init__(self, preset: str = "atlas") -> None:
        # The REAL hardware layout (2,440 addressable LEDs across the cube's
        # corner panels + edge accents), derived from Luke's MadMapper mapping —
        # same interface as the old abstract model, so the engine is untouched.
        self.model = build_hardware_model()
        self.n = int(self.model.n)
        self.eng = VisualEngine(self.model, n_buckets=8)
        self.out = np.zeros((self.n, 3), np.float32)   # JS reads this -> LED colours
        self.feat = np.zeros(_F, np.float32)            # JS writes audio features here
        self.preset = ""
        # Keep the cube's structure (the synthesised beams/columns) always legible
        # in the preview: a constant dim glow floor on those pixels, so the full
        # frame stays visible even when an audio-reactive effect leaves them dark.
        self._structural = getattr(self.model, "structural_mask", np.zeros(self.n, bool))
        self._base_glow = np.array([0.10, 0.13, 0.18], np.float32)  # dim cool-white outline
        self.load(preset)

    # --- one-time geometry for the renderer -------------------------------
    def positions(self) -> np.ndarray:
        """Flat (N*3,) float32 of LED xyz (already centred on the origin)."""
        return np.ascontiguousarray(self.model.positions, dtype=np.float32).ravel()

    def preset_list(self):
        return list(presets.PRESET_ORDER)

    def preset_source(self, name: str) -> str:
        """The real .py source of a built-in preset, with package-relative imports
        rewritten to absolute so the edited copy runs standalone via load_code()."""
        import os
        import re
        path = os.path.join(os.path.dirname(presets.__file__), name + ".py")
        try:
            src = open(path).read()
        except OSError:
            return ""
        return re.sub(r"(?m)^from \.\.", "from cube_dance.", src)

    # --- schema (knobs + trigger pads) for the on-screen controller -------
    def _schema(self, name):
        return {
            "ok": True, "name": name,
            "knobs": [{"label": k.label, "effect": k.effect, "value": float(v)}
                      for k, v in zip(self.eng.knob_spec, self.eng.knob_vals)],
            "triggers": [{"label": lbl, "hold": bool(self.eng.triggers[lbl].hold),
                          "color": list(self.eng.triggers[lbl].color)}
                         for lbl in self.eng.trigger_order],
        }

    def load(self, name: str):
        try:
            self.eng = VisualEngine(self.model, n_buckets=8)
            presets.load(name, self.eng)
            self.preset = name
            return self._schema(name)
        except Exception:  # noqa: BLE001
            import traceback
            return {"ok": False, "error": traceback.format_exc()}

    def load_code(self, src: str, name: str = "dropped"):
        """Preview a dragged-in .py effect. Same contract as a preset module:
        it may define ``build(engine)``, ``KNOBS``, ``TRIGGERS`` -- or an
        ``Element`` subclass named ``Effect``."""
        try:
            ns: dict = {}
            exec(src, ns)  # the user's own file, run in the WASM sandbox
            self.eng = VisualEngine(self.model, n_buckets=8)
            if callable(ns.get("build")):
                ns["build"](self.eng)
            elif "Effect" in ns:
                e = ns["Effect"]
                try:
                    el = e(self.model)        # Element(model) — the common form
                except TypeError:
                    el = e()                  # …or a no-arg Element
                self.eng.add(el)
            else:
                return {"ok": False, "error": "drop a .py with build(engine), or an Element subclass named Effect"}
            self.eng.set_schema(ns.get("KNOBS"), ns.get("TRIGGERS"))
            self.preset = name
            return self._schema(name)
        except Exception:  # noqa: BLE001
            import traceback
            return {"ok": False, "error": traceback.format_exc()}

    # --- live controls ----------------------------------------------------
    def set_knob(self, i: int, v: float) -> None:
        if 0 <= i < len(self.eng.knob_vals):
            self.eng.knob_vals[i] = float(v)

    def fire(self, label: str) -> None:
        try:
            self.eng.fire(label)
        except Exception:  # noqa: BLE001
            pass

    # --- F1 buttons -------------------------------------------------------
    def set_flag(self, name: str, on: bool) -> None:
        """Toggle a VisualParams flag the engine honours (mono/reverse/freeze/size_boost)."""
        if hasattr(self.eng.vparams, name):
            setattr(self.eng.vparams, name, bool(on))

    def reset_knobs(self):
        """BROWSE: knobs back to the preset defaults; returns the new values."""
        self.eng.knob_vals = [kb.default for kb in self.eng.knob_spec]
        return [float(v) for v in self.eng.knob_vals]

    def clear(self) -> None:
        """Stop row: drop any active transients."""
        self.eng.transients = []

    # --- the frame --------------------------------------------------------
    def step(self, t: float) -> None:
        b = self.feat
        evs = [_Ev("kick", float(b[8]) or 1.0)] if b[7] > 0.5 else []
        feats = Features(
            level=float(b[0]), bass=float(b[1]), mid=float(b[2]), treble=float(b[3]),
            bass_l=float(b[4]), bass_r=float(b[5]),
            buckets_l=np.asarray(b[9:17], np.float32), buckets_r=np.asarray(b[17:25], np.float32),
            events=evs, beat=float(b[6]),
            # (m,2) stereo waveform for scope effects — atlas's oscilloscope reads this.
            wave=np.stack([np.asarray(b[25:25 + _WAVE_M], np.float32),
                           np.asarray(b[25 + _WAVE_M:25 + 2 * _WAVE_M], np.float32)], axis=1),
        )
        self.out[:] = 0.0
        self.eng.render(self.model, float(t), feats, self.out)
        # Floor the structural beams/columns to a dim glow so the cube outline is
        # always visible (max, so a brighter effect still shows through).
        if self._structural.any():
            sm = self._structural
            self.out[sm] = np.maximum(self.out[sm], self._base_glow)
        np.clip(self.out, 0.0, 1.0, self.out)


BRIDGE = Bridge("atlas")
