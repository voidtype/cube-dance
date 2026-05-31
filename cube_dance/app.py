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
from .led_topology import build_model
from .recording import SessionRecorder
from .render.camera import FlyCamera, OrbitCamera
from .render.hud import HudOverlay
from .render.scene import CubeScene
from .visuals import Features, PlaceholderVisual, VuMeter


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _control_lines(mode: str, paused: bool, audio_line: str | None = None) -> list[str]:
    common = [
        "Tab  switch nav mode    H  hide help",
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
        self.audio: AudioSource | None = None
        if type(self).audio_file is not None:
            self.audio = AudioSource(type(self).audio_file, mute=type(self).mute, loop=type(self).loop)
            self.visual = VuMeter(self.model)
            self.audio.start()
        else:
            self.visual = PlaceholderVisual()

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
        self.mode = "orbit"

        w, h = self.wnd.buffer_size
        self._set_aspect(w, h)

        self._left = getattr(getattr(self.wnd, "mouse", None), "left", 1)
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
        src = "demo/audio VU meter" if self.audio is not None else "placeholder pattern"
        print(f"Cube Dance — Phase 1 ({src})")
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
        return (
            f"K play/pause  J restart   "
            f"{_fmt_time(self.audio.position)} / {_fmt_time(self.audio.duration)}  [{state}]"
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

    # --- Render loop ---------------------------------------------------------
    def on_render(self, render_time: float, frame_time: float) -> None:
        if self.mode == "fly":
            self._fly_step(frame_time)

        if self.audio is not None:
            self.audio.update(frame_time)
            t = self.audio.position
            features = Features(level=self.audio.level())
        else:
            if not self.paused:
                self._pattern_time += frame_time
            t = self._pattern_time
            features = Features()
        self.visual.update(self.model, t, features)
        self.scene.update_colors()

        self.ctx.clear(0.02, 0.02, 0.03)
        cam = self._cam()
        viewport_h = self.wnd.buffer_size[1]
        ps = CubeScene.proj_scale(viewport_h, cam.fovy_deg)
        self.scene.render(cam.view_bytes(), cam.proj_bytes(), ps)

        # Capture the clean scene (before the HUD) for the recorder. Pace frame
        # count to wall-clock (duplicate when behind) so A/V stays in sync.
        if self.recorder.is_recording:
            n = self.recorder.frames_due(time.time())
            if n > 0:
                fb = self.wnd.fbo
                fw, fh = fb.size
                self.recorder.write_frame(fb.read(components=3), fw, fh, n)

        if self.show_help or self.recorder.is_recording:
            w, h = self.wnd.buffer_size
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

    def on_mouse_press_event(self, x: int, y: int, button: int) -> None:
        self._buttons.add(button)

    def on_mouse_release_event(self, x: int, y: int, button: int) -> None:
        self._buttons.discard(button)

    def on_mouse_position_event(self, x: int, y: int, dx: int, dy: int) -> None:
        # Fly-mode mouse-look when the cursor is captured.
        if self.mode == "fly" and getattr(self.wnd, "mouse_exclusivity", False):
            self.fly.look(dx, dy)

    def on_mouse_drag_event(self, x: int, y: int, dx: int, dy: int) -> None:
        if self.mode == "fly":
            self.fly.look(dx, dy)
            return
        non_left = any(b != self._left for b in self._buttons)
        if self._shift or non_left:
            self.orbit.pan(dx, dy)
        else:
            self.orbit.rotate(dx, dy)

    def on_mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
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
    record_auto: bool = False,
    record_fps: int = 30,
    record_dir: str = "recordings",
) -> None:
    """Launch the interactive viewer. ``extra_args`` is passed to moderngl-window."""
    CubeWindow.config_overrides = config_overrides or {}
    CubeWindow.audio_file = audio_file
    CubeWindow.mute = mute
    CubeWindow.loop = loop
    CubeWindow.record_auto = record_auto
    CubeWindow.record_fps = record_fps
    CubeWindow.record_dir = record_dir
    args = list(extra_args or [])
    if not any(a in ("-wnd", "--window") for a in args):
        args += ["--window", "glfw"]  # reliable core profile on macOS
    mglw.run_window_config(CubeWindow, args=args)
