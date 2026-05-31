"""moderngl rendering: emissive LED strips (tubes) + truss + scenery.

LEDs are drawn as thin **emissive tube geometry** (one tube per LED run), not
point sprites. Solid geometry has proper per-fragment depth, so beams occlude and
are occluded correctly with no popping, and brightness is independent of the view
angle (no additive sprite pile-up). Per-pixel colour comes from the LED color
buffer uploaded as a 1-D texture and sampled along each tube. Everything in the
3D scene is opaque (depth test + write); the HUD does its own alpha blending.
"""

from __future__ import annotations

import math

import moderngl as mgl

from ..led_mesh import build_led_strips
from ..led_topology import CubeModel
from ..scenery import build_solids, build_speaker_markers
from ..truss import build_truss

# Emissive LED strip: colour sampled per-pixel from the LED color texture.
LED_STRIP_VERTEX_SHADER = """
#version 330
uniform mat4 u_view;
uniform mat4 u_proj;
in vec3 in_pos;
in vec3 in_normal;
in float in_uv;
out float v_uv;
out vec3 v_n;
out vec3 v_vpos;
void main() {
    vec4 vp = u_view * vec4(in_pos, 1.0);
    v_vpos = vp.xyz;
    v_n = mat3(u_view) * in_normal;
    v_uv = in_uv;
    gl_Position = u_proj * vp;
}
"""

LED_STRIP_FRAGMENT_SHADER = """
#version 330
uniform sampler2D u_colors;
in float v_uv;
in vec3 v_n;
in vec3 v_vpos;
out vec4 f_color;
void main() {
    vec3 c = texture(u_colors, vec2(v_uv, 0.5)).rgb;   // per-pixel LED colour
    vec3 n = normalize(v_n);
    vec3 vd = normalize(-v_vpos);
    float rim = pow(1.0 - max(dot(n, vd), 0.0), 2.0) * 0.30;  // subtle edge pop
    f_color = vec4(c * (1.0 + rim), 1.0);                      // emissive
}
"""

# Small opaque points for the speaker marker LEDs.
MARKER_VERTEX_SHADER = """
#version 330
uniform mat4 u_view;
uniform mat4 u_proj;
uniform float u_psize;
in vec3 in_pos;
in vec3 in_color;
out vec3 v_color;
void main() {
    gl_Position = u_proj * u_view * vec4(in_pos, 1.0);
    gl_PointSize = u_psize;
    v_color = in_color;
}
"""

MARKER_FRAGMENT_SHADER = """
#version 330
in vec3 v_color;
out vec4 f_color;
void main() {
    if (length(gl_PointCoord - vec2(0.5)) > 0.5) discard;
    f_color = vec4(v_color, 1.0);
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

METAL_VERTEX_SHADER = """
#version 330
uniform mat4 u_view;
uniform mat4 u_proj;
in vec3 in_pos;
in vec3 in_normal;
out vec3 v_n;
out vec3 v_vpos;
void main() {
    vec4 vp = u_view * vec4(in_pos, 1.0);
    v_vpos = vp.xyz;
    v_n = mat3(u_view) * in_normal;
    gl_Position = u_proj * vp;
}
"""

METAL_FRAGMENT_SHADER = """
#version 330
in vec3 v_n;
in vec3 v_vpos;
out vec4 f_color;
uniform vec3 u_color;
void main() {
    vec3 n = normalize(v_n);
    vec3 l = normalize(vec3(0.3, 0.8, 0.6));
    vec3 vdir = normalize(-v_vpos);
    if (dot(n, vdir) < 0.0) n = -n;
    float diff = max(dot(n, l), 0.0);
    vec3 half_v = normalize(l + vdir);
    float spec = pow(max(dot(n, half_v), 0.0), 20.0) * 0.30;
    float fres = pow(1.0 - max(dot(n, vdir), 0.0), 3.0) * 0.12;
    vec3 c = u_color * (0.22 + 0.55 * diff) + vec3(spec) + vec3(fres);
    f_color = vec4(c, 1.0);
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
        led_surface_offset_m: float = 0.032,
        marker_px: float = 9.0,
        ambient: float = 0.55,
    ) -> None:
        self.ctx = ctx
        self.model = model
        self.cfg = model.cfg
        self.marker_px = marker_px
        self.ambient = ambient

        self.strip_prog = ctx.program(
            vertex_shader=LED_STRIP_VERTEX_SHADER, fragment_shader=LED_STRIP_FRAGMENT_SHADER
        )
        self.marker_prog = ctx.program(
            vertex_shader=MARKER_VERTEX_SHADER, fragment_shader=MARKER_FRAGMENT_SHADER
        )
        self.solid_prog = ctx.program(vertex_shader=SOLID_VERTEX_SHADER, fragment_shader=SOLID_FRAGMENT_SHADER)
        self.metal_prog = ctx.program(vertex_shader=METAL_VERTEX_SHADER, fragment_shader=METAL_FRAGMENT_SHADER)

        # LED color buffer as a 1-D (N x 1) texture, sampled along each strip.
        self._color_tex = ctx.texture((model.n, 1), 3, dtype="f4")
        self._color_tex.filter = (mgl.LINEAR, mgl.LINEAR)
        self.update_colors()

        # Emissive LED strip geometry (one tube per run); static positions.
        offset = led_surface_offset_m if self.cfg.show_truss else 0.0
        s_pos, s_nrm, s_uv = build_led_strips(model, radius=led_radius_m, offset=offset)
        self._strip_n = s_pos.shape[0]
        sp = ctx.buffer(s_pos.tobytes())
        sn = ctx.buffer(s_nrm.tobytes())
        su = ctx.buffer(s_uv.tobytes())
        self.strip_vao = ctx.vertex_array(
            self.strip_prog,
            [(sp, "3f", "in_pos"), (sn, "3f", "in_normal"), (su, "1f", "in_uv")],
        )

        # Solid scenery (ground + speakers + bushes) -- one combined draw.
        g_pos, g_nrm, g_col = build_solids(self.cfg)
        self._solid_n = g_pos.shape[0]
        self.solid_vao = None
        if self._solid_n:
            self.solid_vao = ctx.vertex_array(
                self.solid_prog,
                [(ctx.buffer(g_pos.tobytes()), "3f", "in_pos"),
                 (ctx.buffer(g_nrm.tobytes()), "3f", "in_normal"),
                 (ctx.buffer(g_col.tobytes()), "3f", "in_color")],
            )

        # Dull-aluminium truss.
        self.truss_vao = None
        self._truss_n = 0
        if self.cfg.show_truss:
            t_pos, t_nrm = build_truss(self.cfg)
            self._truss_n = t_pos.shape[0]
            self.truss_vao = ctx.vertex_array(
                self.metal_prog,
                [(ctx.buffer(t_pos.tobytes()), "3f", "in_pos"), (ctx.buffer(t_nrm.tobytes()), "3f", "in_normal")],
            )

        # Speaker marker LEDs.
        self.marker_vao = None
        self._marker_n = 0
        if self.cfg.show_speakers:
            m_pos, m_col = build_speaker_markers(self.cfg)
            self._marker_n = m_pos.shape[0]
            self.marker_vao = ctx.vertex_array(
                self.marker_prog,
                [(ctx.buffer(m_pos.tobytes()), "3f", "in_pos"), (ctx.buffer(m_col.tobytes()), "3f", "in_color")],
            )

    def update_colors(self) -> None:
        self._color_tex.write(self.model.colors.astype("f4").tobytes())

    @staticmethod
    def proj_scale(viewport_height: int, fovy_deg: float) -> float:
        return viewport_height / (2.0 * math.tan(math.radians(fovy_deg) / 2.0))

    def render(self, view_bytes: bytes, proj_bytes: bytes, proj_scale: float) -> None:
        ctx = self.ctx
        ctx.enable(mgl.DEPTH_TEST)
        ctx.disable(mgl.BLEND)  # whole 3D scene is opaque; the HUD blends separately

        if self.solid_vao is not None:
            self.solid_prog["u_view"].write(view_bytes)
            self.solid_prog["u_proj"].write(proj_bytes)
            _set(self.solid_prog, "u_ambient", float(self.ambient))
            self.solid_vao.render(mgl.TRIANGLES, vertices=self._solid_n)

        if self.truss_vao is not None:
            self.metal_prog["u_view"].write(view_bytes)
            self.metal_prog["u_proj"].write(proj_bytes)
            _set(self.metal_prog, "u_color", (0.40, 0.42, 0.45))
            self.truss_vao.render(mgl.TRIANGLES, vertices=self._truss_n)

        # Emissive LED strips (opaque solid tubes -> view-independent brightness).
        self._color_tex.use(0)
        self.strip_prog["u_view"].write(view_bytes)
        self.strip_prog["u_proj"].write(proj_bytes)
        _set(self.strip_prog, "u_colors", 0)
        self.strip_vao.render(mgl.TRIANGLES, vertices=self._strip_n)

        if self.marker_vao is not None:
            ctx.enable(mgl.PROGRAM_POINT_SIZE)
            self.marker_prog["u_view"].write(view_bytes)
            self.marker_prog["u_proj"].write(proj_bytes)
            _set(self.marker_prog, "u_psize", float(self.marker_px))
            self.marker_vao.render(mgl.POINTS, vertices=self._marker_n)
