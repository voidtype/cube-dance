"""A small orbit camera with numpy matrix math.

Implemented directly (rather than using a moderngl-window camera class) so it
behaves identically across window backends and versions. Matrices are built
row-major (``M @ column_vector``); use the ``*_bytes`` helpers to upload them to
OpenGL, which expects column-major data (hence the transpose).
"""

from __future__ import annotations

import math

import numpy as np


def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def perspective(fovy_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    aspect = aspect if aspect > 1e-6 else 1.0
    m = np.zeros((4, 4), dtype=np.float64)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = _normalize(center - eye)
    s = _normalize(np.cross(f, up))
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float64)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


class OrbitCamera:
    """Orbit around ``target`` at ``distance``, controlled by azimuth/elevation."""

    def __init__(
        self,
        target: tuple[float, float, float] = (0.0, 0.0, 0.0),
        distance: float = 5.0,
        azimuth_deg: float = 35.0,
        elevation_deg: float = 20.0,
        fovy_deg: float = 45.0,
        near: float = 0.05,
        far: float = 100.0,
        min_distance: float = 1.0,
        max_distance: float = 30.0,
    ) -> None:
        self._home = dict(
            target=np.array(target, dtype=np.float64),
            distance=distance,
            azimuth_deg=azimuth_deg,
            elevation_deg=elevation_deg,
        )
        self.fovy_deg = fovy_deg
        self.near = near
        self.far = far
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.aspect = 1.0
        self.rotate_speed = 0.4
        self.zoom_speed = 0.12
        self.pan_speed = 0.0015
        self.reset()

    def reset(self) -> None:
        self.target = self._home["target"].copy()
        self.distance = float(self._home["distance"])
        self.azimuth_deg = float(self._home["azimuth_deg"])
        self.elevation_deg = float(self._home["elevation_deg"])

    # --- Interaction ---------------------------------------------------------
    def rotate(self, dx: float, dy: float) -> None:
        self.azimuth_deg -= dx * self.rotate_speed
        self.elevation_deg = max(-89.0, min(89.0, self.elevation_deg + dy * self.rotate_speed))

    def zoom(self, scroll: float) -> None:
        self.distance *= 0.9 ** scroll
        self.distance = max(self.min_distance, min(self.max_distance, self.distance))

    def pan(self, dx: float, dy: float) -> None:
        view = self.view_matrix()
        right = view[0, :3]
        up = view[1, :3]
        k = self.pan_speed * self.distance
        self.target += (-right * dx + up * dy) * k

    # --- Matrices ------------------------------------------------------------
    def eye(self) -> np.ndarray:
        el = math.radians(self.elevation_deg)
        az = math.radians(self.azimuth_deg)
        direction = np.array(
            [math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)]
        )
        return self.target + self.distance * direction

    def view_matrix(self) -> np.ndarray:
        return look_at(self.eye(), self.target, np.array([0.0, 1.0, 0.0]))

    def proj_matrix(self) -> np.ndarray:
        return perspective(self.fovy_deg, self.aspect, self.near, self.far)

    def view_bytes(self) -> bytes:
        return self.view_matrix().T.astype("f4").tobytes()

    def proj_bytes(self) -> bytes:
        return self.proj_matrix().T.astype("f4").tobytes()

    def set_from_eye_forward(self, eye: np.ndarray, forward: np.ndarray) -> None:
        """Re-aim the orbit camera to match a free-fly eye + look direction."""
        forward = _normalize(forward)
        self.target = eye + forward * self.distance
        d = -forward  # eye sits along -forward from target
        self.azimuth_deg = math.degrees(math.atan2(d[0], d[2]))
        self.elevation_deg = math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))


class FlyCamera:
    """Free-fly / FPS camera: WASD move + mouse-look."""

    def __init__(
        self,
        position: tuple[float, float, float] = (0.0, 0.0, 6.0),
        yaw_deg: float = 180.0,
        pitch_deg: float = 0.0,
        fovy_deg: float = 45.0,
        near: float = 0.05,
        far: float = 100.0,
        move_speed: float = 3.0,
        look_speed: float = 0.15,
    ) -> None:
        self.position = np.array(position, dtype=np.float64)
        self.yaw_deg = yaw_deg
        self.pitch_deg = pitch_deg
        self.fovy_deg = fovy_deg
        self.near = near
        self.far = far
        self.move_speed = move_speed
        self.look_speed = look_speed
        self.aspect = 1.0

    def forward(self) -> np.ndarray:
        p = math.radians(self.pitch_deg)
        y = math.radians(self.yaw_deg)
        return np.array([math.cos(p) * math.sin(y), math.sin(p), math.cos(p) * math.cos(y)])

    def look(self, dx: float, dy: float) -> None:
        self.yaw_deg -= dx * self.look_speed
        self.pitch_deg = max(-89.0, min(89.0, self.pitch_deg - dy * self.look_speed))

    def move(self, dt: float, fwd: float, strafe: float, up: float, speed_mult: float = 1.0) -> None:
        f = self.forward()
        world_up = np.array([0.0, 1.0, 0.0])
        right = _normalize(np.cross(f, world_up))
        step = self.move_speed * speed_mult * dt
        self.position += (f * fwd + right * strafe + world_up * up) * step

    def view_matrix(self) -> np.ndarray:
        return look_at(self.position, self.position + self.forward(), np.array([0.0, 1.0, 0.0]))

    def proj_matrix(self) -> np.ndarray:
        return perspective(self.fovy_deg, self.aspect, self.near, self.far)

    def view_bytes(self) -> bytes:
        return self.view_matrix().T.astype("f4").tobytes()

    def proj_bytes(self) -> bytes:
        return self.proj_matrix().T.astype("f4").tobytes()

    def set_from_orbit(self, orbit: "OrbitCamera") -> None:
        """Place the fly camera at the orbit eye, looking at the orbit target."""
        eye = orbit.eye()
        self.position = eye.copy()
        f = _normalize(orbit.target - eye)
        self.yaw_deg = math.degrees(math.atan2(f[0], f[2]))
        self.pitch_deg = math.degrees(math.asin(max(-1.0, min(1.0, f[1]))))
