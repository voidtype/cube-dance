"""moderngl rendering: emissive LED points + optional solid scenery.

LEDs upload once (static positions) plus a dynamic color buffer rewritten each
frame from ``model.colors`` in a single ``buffer.write``, drawn in one ``POINTS``
call. Solid scenery (clay ground, speaker cabinets, bushes) draws first with
depth writes so it can occlude LEDs behind it; the LEDs and speaker marker dots
then draw additively with depth-testing on but depth-writes off, so their glow
still accumulates.
"""

from __future__ import annotations

import math

import moderngl as mgl
import numpy as np

from ..led_topology import CubeModel
from ..scenery import build_solids, build_speaker_markers

# Shader sources are module-level so the headless self-test can compile them.
LED_VERTEX_SHADER = """
#version 330
uniform mat4 u_view;
uniform mat4 u_proj;
uniform float u_proj_scale;
uniform float u_radius;
uniform float u_min_px;
uniform float u_max_px;
in vec3 in_pos;
in vec3 in_color;
out vec3 v_color;
void main() {
    vec4 vpos = u_view * vec4(in_pos, 1.0);
    gl_Position = u_proj * vpos;
    float z = max(-vpos.z, 0.001);
    gl_PointSize = clamp(2.0 * u_radius * u_proj_scale / z, u_min_px, u_max_px);
    v_color = in_color;
}
"""

LED_FRAGMENT_SHADER = """
#version 330
in vec3 v_color;
out vec4 f_color;
void main() {
    float r = length(gl_PointCoord - vec2(0.5)) * 2.0;
    if (r > 1.0) discard;
    f_color = vec4(v_color * exp(-r * r * 4.0), 1.0);
}
"""

SOLID_VERTEX_SHADER = """
#version 330
uniform mat4 u_view;
uniform mat4 u_proj;
in vec3 in_pos;
in vec3 in_normal;
in vec3 in_color;
out vec3 v_n;
out vec3 v_color;
void main() {
    v_n = mat3(u_view) * in_normal;
    v_color = in_color;
    gl_Position = u_proj * u_view * vec4(in_pos, 1.0);
}
"""

SOLID_FRAGMENT_SHADER = """
#version 330
in vec3 v_n;
in vec3 v_color;
out vec4 f_color;
uniform float u_ambient;
void main() {
    vec3 n = normalize(v_n);
    float diff = max(dot(n, normalize(vec3(0.3, 0.8, 0.6))), 0.0);
    f_color = vec4(v_color * (u_ambient + (1.0 - u_ambient) * diff), 1.0);
}
"""


def _set(prog: mgl.Program, name: str, value) -> None:
    try:
        prog[name].value = value
    except KeyError:
        pass


class CubeScene:
    def __init__(
        self,
        ctx: mgl.Context,
        model: CubeModel,
        *,
        led_radius_m: float = 0.012,
        marker_radius_m: float = 0.03,
        ambient: float = 0.55,
        min_px: float = 1.5,
        max_px: float = 48.0,
    ) -> None:
        self.ctx = ctx
        self.model = model
        self.cfg = model.cfg
        self.led_radius_m = led_radius_m
        self.marker_radius_m = marker_radius_m
        self.ambient = ambient
        self.min_px = min_px
        self.max_px = max_px

        self.led_prog = ctx.program(vertex_shader=LED_VERTEX_SHADER, fragment_shader=LED_FRAGMENT_SHADER)
        self.solid_prog = ctx.program(vertex_shader=SOLID_VERTEX_SHADER, fragment_shader=SOLID_FRAGMENT_SHADER)

        # LEDs: static positions + dynamic colors.
        self._pos_vbo = ctx.buffer(model.positions.astype("f4").tobytes())
        self._col_vbo = ctx.buffer(model.colors.astype("f4").tobytes(), dynamic=True)
        self.led_vao = ctx.vertex_array(
            self.led_prog, [(self._pos_vbo, "3f", "in_pos"), (self._col_vbo, "3f", "in_color")]
        )

        # Solid scenery (ground + speakers + bushes) -- one combined draw.
        s_pos, s_nrm, s_col = build_solids(self.cfg)
        self._solid_n = s_pos.shape[0]
        self.solid_vao = None
        if self._solid_n:
            spos = ctx.buffer(s_pos.tobytes())
            snrm = ctx.buffer(s_nrm.tobytes())
            scol = ctx.buffer(s_col.tobytes())
            self.solid_vao = ctx.vertex_array(
                self.solid_prog,
                [(spos, "3f", "in_pos"), (snrm, "3f", "in_normal"), (scol, "3f", "in_color")],
            )

        # Speaker marker LEDs (blue, additive points).
        self.marker_vao = None
        self._marker_n = 0
        if self.cfg.show_speakers:
            m_pos, m_col = build_speaker_markers(self.cfg)
            self._marker_n = m_pos.shape[0]
            mpos = ctx.buffer(m_pos.tobytes())
            mcol = ctx.buffer(m_col.tobytes())
            self.marker_vao = ctx.vertex_array(
                self.led_prog, [(mpos, "3f", "in_pos"), (mcol, "3f", "in_color")]
            )

        self._has_depth_mask = hasattr(ctx, "depth_mask")

    def update_colors(self) -> None:
        self._col_vbo.write(self.model.colors.astype("f4").tobytes())

    @staticmethod
    def proj_scale(viewport_height: int, fovy_deg: float) -> float:
        return viewport_height / (2.0 * math.tan(math.radians(fovy_deg) / 2.0))

    def render(self, view_bytes: bytes, proj_bytes: bytes, proj_scale: float) -> None:
        ctx = self.ctx

        # --- Opaque scenery first (writes depth so it occludes LEDs behind it) ---
        ctx.enable(mgl.DEPTH_TEST)
        if self._has_depth_mask:
            ctx.depth_mask = True
        if self.solid_vao is not None:
            ctx.disable(mgl.BLEND)
            self.solid_prog["u_view"].write(view_bytes)
            self.solid_prog["u_proj"].write(proj_bytes)
            _set(self.solid_prog, "u_ambient", float(self.ambient))
            self.solid_vao.render(mgl.TRIANGLES, vertices=self._solid_n)

        # --- Additive emissive elements: depth-test on, depth-write off ---
        ctx.enable(mgl.BLEND)
        ctx.blend_func = (mgl.ONE, mgl.ONE)
        if self._has_depth_mask:
            ctx.depth_mask = False
        ctx.enable(mgl.PROGRAM_POINT_SIZE)

        self.led_prog["u_view"].write(view_bytes)
        self.led_prog["u_proj"].write(proj_bytes)
        _set(self.led_prog, "u_proj_scale", float(proj_scale))
        _set(self.led_prog, "u_min_px", float(self.min_px))
        _set(self.led_prog, "u_max_px", float(self.max_px))
        _set(self.led_prog, "u_radius", float(self.led_radius_m))
        self.led_vao.render(mgl.POINTS, vertices=self.model.n)

        if self.marker_vao is not None:
            _set(self.led_prog, "u_radius", float(self.marker_radius_m))
            self.marker_vao.render(mgl.POINTS, vertices=self._marker_n)

        if self._has_depth_mask:
            ctx.depth_mask = True
