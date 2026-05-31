"""Interactive native viewer (moderngl-window).

Wires the cube model, placeholder pattern, scene, and cameras into a real-time
render loop with two navigation modes (orbit / fly) and an on-screen help HUD.
This is the view layer only -- it reads/writes the shared ``model.colors`` buffer
and nothing more, so later phases drive that buffer without touching rendering.
"""

from __future__ import annotations

import dataclasses
import math
import time

import moderngl_window as mglw

from .audio import AudioSource
from .config import CubeConfig
from .control import ControlMap, ControlState
from .control.midi import MidiInput
from .led_topology import build_model
from .recording import SessionRecorder
from .render.camera import FlyCamera, OrbitCamera
from .render.hud import HudOverlay
from .render.scene import CubeScene
from .render.virtual_f1 import VirtualF1
from .visuals import Features, PlaceholderVisual, VuMeter
from .visuals.engine.mixer import DeckMixer
from .visuals.params import VisualParams
from . import presets


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _control_lines(mode: str, paused: bool, audio_line: str | None = None) -> list[str]:
    common = [
        "Tab  switch nav mode    H  hide help    C  controls",
        "R  reset view    V  record    Esc  quit",
    ]
    if mode == "orbit":
        head = ["NAV: ORBIT (3D-editor)", "Left-drag orbit | Shift/right-drag pan | Scroll zoom"]
    else:
        head = ["NAV: FLY (FPS)", "WASD move | mouse look | Space/E up | Ctrl/Q down | Shift fast | Scroll speed"]
    if audio_line is not None:
        head.append(audio_line)
    elif paused:
        head[0] += "   [PATTERN PAUSED]"
    return head + common


class CubeWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Cube Dance — Phase 0"
    window_size = (1280, 800)
    aspect_ratio = None
    resizable = True
    vsync = True
    samples = 4

    config_overrides: dict = {}
    audio_file = None  # set by the CLI (an AudioFile) to drive a VU meter
    mute: bool = False
    loop: bool = False
    visual_choice: str = "auto"
    preset: str = "deep"
    record_auto: bool = False
    record_fps: int = 30
    record_dir: str = "recordings"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        valid = {f.name for f in dataclasses.fields(CubeConfig)}
        overrides = {k: v for k, v in self.config_overrides.items() if k in valid and v is not None}
        self.cfg = CubeConfig(**overrides)
        self.model = build_model(self.cfg)
        self.scene = CubeScene(self.ctx, self.model)
        self.hud = HudOverlay(self.ctx)

        # Audio source + visual selection: VU meter when audio is loaded, else
        # the Phase 0 placeholder pattern.
        # F1 control surface: state + mapping + (optional) MIDI + virtual panel.
        self.controls = ControlState()
        self.control_map = ControlMap()
        self.vparams = VisualParams()
        self.aparams = None
        self.f1 = VirtualF1(self.ctx)
        self.show_controls = False
        self.midi = MidiInput(self.controls)
        self.midi.start()

        self.audio: AudioSource | None = None
        choice = type(self).visual_choice
        self._last_focus = 0
        self._prev_browse = False
        self._pending_fires: list = []  # quantised pad triggers awaiting the next beat
        self._pending_age = 0.0
        self._last_beat = 0.0
        if type(self).audio_file is not None:
            self.audio = AudioSource(type(self).audio_file, mute=type(self).mute, loop=type(self).loop)
            self.aparams = self.audio.processor.p
            if choice == "vu":
                self.visual, self.visual_name = VuMeter(self.model), "vu"
            else:  # auto / spectrum -> 4-deck preset mixer
                deck_presets = list(presets.PRESET_ORDER)[:4]
                if type(self).preset in presets.PRESET_ORDER:
                    deck_presets[0] = type(self).preset  # --preset seeds deck 1
                self.visual = DeckMixer(
                    self.model, n_buckets=self.audio.analyzer.n_buckets,
                    vparams=self.vparams, deck_presets=deck_presets,
                )
                self.visual_name = "mixer"
            self.audio.start()
        else:
            self.visual, self.visual_name = PlaceholderVisual(), "placeholder"

        self.recorder = SessionRecorder(
            self.audio, loop=type(self).loop, fps=type(self).record_fps, outdir=type(self).record_dir
        )

        fovy = 45.0
        radius = self.cfg.half * math.sqrt(3.0)
        fit = radius / math.sin(math.radians(fovy / 2.0)) * 1.15
        self.orbit = OrbitCamera(
            distance=fit, fovy_deg=fovy, min_distance=self.cfg.half, max_distance=self.cfg.side_m * 8.0
        )
        self.fly = FlyCamera(fovy_deg=fovy)
        self.fly.set_from_orbit(self.orbit)
        self.mode = "fly"  # WASD by default
        try:
            self.wnd.mouse_exclusivity = True  # capture mouse for fly-look
        except Exception:
            pass

        w, h = self.wnd.buffer_size
        self._set_aspect(w, h)

        self._left = getattr(getattr(self.wnd, "mouse", None), "left", 1)
        self._mouse = (0.0, 0.0)
        self._buttons: set[int] = set()
        self._keys_down: set = set()
        self._shift = False
        self._ctrl = False
        self._pattern_time = 0.0
        self.paused = False
        self.show_help = True
        self._title_accum = 0.0
        self._hud_accum = 0.0

        self._refresh_hud()
        print(f"Cube Dance — visual: {self.visual_name}")
        print("\n".join(_control_lines(self.mode, self.paused, self._audio_line())))
        print(f"Cube model: {self.model.n} LED pixels "
              f"({int(self.model.edge_mask.sum())} edge, {int(self.model.corner_mask.sum())} corner)")

        if type(self).record_auto:
            self._toggle_recording()

    # --- Helpers -------------------------------------------------------------
    def _set_aspect(self, w: int, h: int) -> None:
        a = w / max(h, 1)
        self.orbit.aspect = a
        self.fly.aspect = a

    def _cam(self):
        return self.orbit if self.mode == "orbit" else self.fly

    def _audio_line(self) -> str | None:
        if self.audio is None:
            return None
        state = "PLAYING" if self.audio.playing else "PAUSED"
        tag = self.visual_name
        if isinstance(self.visual, DeckMixer):
            f = int(self.controls.focus_deck) % self.visual.n_decks
            tag = f"mixer · deck {f + 1}:{self.visual.preset_name[f]}"
        return (
            f"K play/pause  J restart   "
            f"{_fmt_time(self.audio.position)} / {_fmt_time(self.audio.duration)}  [{state}]  · {tag}"
        )

    def _rec_line(self) -> str | None:
        if not self.recorder.is_recording:
            return None
        return f"● REC  {_fmt_time(self.recorder.elapsed)}   (V to stop)"

    def _refresh_hud(self) -> None:
        rec = self._rec_line()
        if self.show_help:
            lines = _control_lines(self.mode, self.paused, self._audio_line())
        else:
            lines = []  # help hidden, but still surface the REC indicator
        if rec:
            lines = [rec] + lines
        self.hud.set_text(lines)

    def _toggle_recording(self) -> None:
        if self.recorder.is_recording:
            path = self.recorder.stop()
            if path:
                print(f"[rec] saved {path}")
            elif self.recorder.error:
                print(f"[rec] error: {self.recorder.error}")
        else:
            w, h = self.wnd.fbo.size
            self.recorder.start(w, h)
            if self.recorder.error:
                print(f"[rec] could not start: {self.recorder.error}")
            else:
                print(f"[rec] recording -> {self.recorder._final}")
        self._refresh_hud()

    def _toggle_mode(self) -> None:
        if self.mode == "orbit":
            self.fly.set_from_orbit(self.orbit)
            self.mode = "fly"
            try:
                self.wnd.mouse_exclusivity = True
            except Exception:
                pass
        else:
            self.orbit.set_from_eye_forward(self.fly.position, self.fly.forward())
            self.mode = "orbit"
            try:
                self.wnd.mouse_exclusivity = False
            except Exception:
                pass
        self._refresh_hud()

    def _apply_perf_controls(self, features, dt: float = 0.0) -> None:
        """Route the F1 surface to the mixer: deck volumes, the selected deck's
        preset (encoder) + knob params, and pad triggers (quantised on QUANT)."""
        mx = self.visual
        if not isinstance(mx, DeckMixer):
            return
        c = self.controls
        order = list(presets.PRESET_ORDER)
        n = len(order)
        mx.volumes = list(c.faders)
        focus = int(c.focus_deck) % mx.n_decks

        changed_focus = focus != self._last_focus
        if changed_focus:
            c.p = mx.preset_index[focus]  # display tracks the selected deck
            self._last_focus = focus
            self.f1.mark_dirty()
        target = c.p % n
        if target != c.p:
            c.p = target  # keep the 7-seg display in [0, n-1]
        preset_changed = target != mx.preset_index[focus]
        if preset_changed:
            mx.set_deck_preset(focus, order[target])
            self.f1.mark_dirty()
            print(f"[deck {focus + 1}] {order[target]}")
        if changed_focus or preset_changed:  # load the deck's knob values into the knobs
            c.knobs = mx.knob_vals(focus)
            self.f1.mark_dirty()

        browse = bool(c.buttons.get("BROWSE"))  # BROWSE press -> reset deck knobs
        if browse and not self._prev_browse:
            mx.reset_knobs(focus)
            c.knobs = mx.knob_vals(focus)
            self.f1.mark_dirty()
        self._prev_browse = browse

        for i in range(min(len(c.knobs), len(mx.knob_labels(focus)))):
            mx.set_knob(focus, i, c.knobs[i])

        # Pad triggers: fire now, or queue to the next beat when QUANT is on.
        quant = bool(c.buttons.get("QUANT"))
        beat = float(getattr(features, "beat", 0.0) or 0.0)
        kicked = any(e.kind == "kick" for e in (getattr(features, "events", None) or []))
        # A beat boundary = a detected kick or a beat-phase wrap; with a timeout
        # fallback so a quantised hit always lands within ~0.6 s if none is found.
        boundary = kicked or (self._last_beat > 0.6 and beat < 0.3)
        self._last_beat = beat
        while c.pad_queue:
            col, row = c.pad_queue.pop(0)
            label = mx.trigger_label(col, row)
            if label is None:
                continue
            if quant:
                self._pending_fires.append((col, label))
                self._pending_age = 0.0
            else:
                mx.fire(col, label, 1.0)
        if self._pending_fires:
            self._pending_age += dt
            if boundary or self._pending_age > 0.6:
                for col, label in self._pending_fires:
                    mx.fire(col, label, 1.0)
                self._pending_fires.clear()

    def _bump_focus_preset(self) -> None:
        """Keyboard `N`: advance the selected deck's preset (same as the encoder)."""
        if isinstance(self.visual, DeckMixer):
            self.controls.p = self.controls.p + 1
            self.f1.mark_dirty()

    def _toggle_controls(self) -> None:
        self.show_controls = not self.show_controls
        if self.show_controls:
            self.f1.mark_dirty()
            try:
                self.wnd.mouse_exclusivity = False  # release the cursor to drive the panel
            except Exception:
                pass
        elif self.mode == "fly":
            try:
                self.wnd.mouse_exclusivity = True  # recapture for fly-look
            except Exception:
                pass

    # --- Render loop ---------------------------------------------------------
    def on_render(self, render_time: float, frame_time: float) -> None:
        if self.mode == "fly" and not self.show_controls:  # frozen while controls are up
            self._fly_step(frame_time)

        # Buttons -> global flags; then route faders/encoder/knobs/pads to the mixer.
        if self.audio is not None:
            self.control_map.apply(self.controls, self.vparams)
            self.audio.update(frame_time)
            t = self.audio.position
            features = self.audio.features(frame_time)
            self._apply_perf_controls(features, frame_time)
        else:
            if not self.paused:
                self._pattern_time += frame_time
            t = self._pattern_time
            features = Features()
        self.visual.update(self.model, t, features)
        self._decay_pad_glow(frame_time)
        self.scene.update_colors()

        self.ctx.clear(0.02, 0.02, 0.03)
        cam = self._cam()
        w, h = self.wnd.buffer_size
        ps = CubeScene.proj_scale(h, cam.fovy_deg)
        self.scene.render(cam.view_bytes(), cam.proj_bytes(), ps)

        # The F1 panel is drawn BEFORE the recorder capture so it appears in the
        # video when shown; the HUD help/REC indicator is drawn AFTER (excluded).
        if self.show_controls:
            self._render_f1(w, h)

        if self.recorder.is_recording:
            n = self.recorder.frames_due(time.time())
            if n > 0:
                fb = self.wnd.fbo
                fw, fh = fb.size
                self.recorder.write_frame(fb.read(components=3), fw, fh, n)

        if self.show_help or self.recorder.is_recording:
            self.hud.render(w, h)

        self._title_accum += frame_time
        if self._title_accum >= 0.5:
            self._title_accum = 0.0
            fps = 1.0 / frame_time if frame_time > 0 else 0.0
            try:
                self.wnd.title = f"Cube Dance — {self.model.n} px — {self.mode} — {fps:0.0f} FPS"
            except Exception:
                pass

        # Refresh the HUD a few times a second so the audio position / REC timer tick.
        if (self.audio is not None and self.show_help) or self.recorder.is_recording:
            self._hud_accum += frame_time
            if self._hud_accum >= 0.25:
                self._hud_accum = 0.0
                self._refresh_hud()

    def _render_f1(self, w: int, h: int) -> None:
        mx = self.visual
        if isinstance(mx, DeckMixer):
            focus = int(self.controls.focus_deck) % mx.n_decks
            pad_colors = []
            for c in range(mx.n_decks):
                cells = mx.trigger_cells(c)
                pad_colors.append([cells[r][1] if r < len(cells) else None for r in range(4)])
            self.f1.render(w, h, self.controls, deck_labels=mx.preset_name, focus=focus,
                           knob_labels=mx.knob_labels(focus), pad_colors=pad_colors)
        else:
            self.f1.render(w, h, self.controls)

    def _decay_pad_glow(self, dt: float) -> None:
        """Fade the on-screen pad glow after a hit."""
        c = self.controls
        glow = c.pad_glow
        if not any(g > 0.01 for g in glow):
            return
        k = math.exp(-dt / 0.25) if dt > 0 else 1.0
        c.pad_glow = [g * k for g in glow]
        if self.show_controls:
            self.f1.mark_dirty()

    def _fly_step(self, dt: float) -> None:
        keys = self.wnd.keys
        d = self._keys_down

        def held(*ks) -> bool:
            return any(k in d for k in ks)

        fwd = (1.0 if held(keys.W) else 0.0) - (1.0 if held(keys.S) else 0.0)
        strafe = (1.0 if held(keys.D) else 0.0) - (1.0 if held(keys.A) else 0.0)
        up = (1.0 if held(keys.SPACE, keys.E) else 0.0) - (1.0 if (held(keys.Q) or self._ctrl) else 0.0)
        if fwd or strafe or up:
            self.fly.move(dt, fwd, strafe, up, speed_mult=3.0 if self._shift else 1.0)

    def on_resize(self, width: int, height: int) -> None:
        self._set_aspect(width, height)

    # --- Input ---------------------------------------------------------------
    def on_key_event(self, key, action, modifiers) -> None:
        keys = self.wnd.keys
        self._shift = bool(getattr(modifiers, "shift", False))
        self._ctrl = bool(getattr(modifiers, "ctrl", False))
        if action == keys.ACTION_PRESS:
            self._keys_down.add(key)
            if key == keys.ESCAPE:
                self.wnd.close()
            elif key == keys.TAB:
                self._toggle_mode()
            elif key == keys.H:
                self.show_help = not self.show_help
                self._refresh_hud()
            elif key == keys.R:
                self.orbit.reset()
                self.fly.set_from_orbit(self.orbit)
            elif key == keys.V:
                self._toggle_recording()
            elif key == keys.C:
                self._toggle_controls()
            elif key == keys.N and self.audio is not None:
                self._bump_focus_preset()
            elif key == keys.K and self.audio is not None:
                self.audio.toggle()
                self._refresh_hud()
            elif key == keys.J and self.audio is not None:
                self.audio.restart()
                self._refresh_hud()
            elif key == keys.P and self.audio is None:
                self.paused = not self.paused
                self._refresh_hud()
        elif action == keys.ACTION_RELEASE:
            self._keys_down.discard(key)

    def on_close(self) -> None:
        if self.recorder.is_recording:
            path = self.recorder.stop()
            if path:
                print(f"[rec] saved {path}")
        if self.audio is not None:
            self.audio.close()
        self.midi.close()

    def on_mouse_press_event(self, x: int, y: int, button: int) -> None:
        if self.show_controls and self.f1.contains(x, y):
            self.f1.on_press(x, y, self.controls)
            return
        self._buttons.add(button)

    def on_mouse_release_event(self, x: int, y: int, button: int) -> None:
        if self.show_controls:
            self.f1.on_release()
            return
        self._buttons.discard(button)

    def on_mouse_position_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._mouse = (x, y)
        if self.show_controls:
            return  # no fly-look while the controls panel is up
        if self.mode == "fly" and getattr(self.wnd, "mouse_exclusivity", False):
            self.fly.look(dx, dy)

    def on_mouse_drag_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self._mouse = (x, y)
        if self.show_controls:
            self.f1.on_drag(x, y, self.controls)
            return
        if self.mode == "fly":
            self.fly.look(dx, dy)
            return
        non_left = any(b != self._left for b in self._buttons)
        if self._shift or non_left:
            self.orbit.pan(dx, dy)
        else:
            self.orbit.rotate(dx, dy)

    def on_mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
        if self.show_controls:
            mx, my = self._mouse
            self.f1.on_scroll(mx, my, 1 if y_offset > 0 else -1, self.controls)
            return
        if self.mode == "fly":
            self.fly.move_speed = max(0.3, min(30.0, self.fly.move_speed * (1.1 ** y_offset)))
        else:
            self.orbit.zoom(y_offset)


def run(
    config_overrides: dict | None = None,
    extra_args: list[str] | None = None,
    audio_file=None,
    mute: bool = False,
    loop: bool = False,
    visual_choice: str = "auto",
    preset: str = "deep",
    record_auto: bool = False,
    record_fps: int = 30,
    record_dir: str = "recordings",
) -> None:
    """Launch the interactive viewer. ``extra_args`` is passed to moderngl-window."""
    CubeWindow.config_overrides = config_overrides or {}
    CubeWindow.audio_file = audio_file
    CubeWindow.mute = mute
    CubeWindow.loop = loop
    CubeWindow.visual_choice = visual_choice
    CubeWindow.preset = preset
    CubeWindow.record_auto = record_auto
    CubeWindow.record_fps = record_fps
    CubeWindow.record_dir = record_dir
    args = list(extra_args or [])
    if not any(a in ("-wnd", "--window") for a in args):
        args += ["--window", "glfw"]  # reliable core profile on macOS
    mglw.run_window_config(CubeWindow, args=args)
