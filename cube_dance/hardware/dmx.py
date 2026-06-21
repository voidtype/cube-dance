"""Protocol-neutral DMX-over-IP core: the channel layout + a sink base class.

The cube's colour frame is packed into per-universe DMX channel buffers here; the
two wire protocols (ArtNet in :mod:`.artnet`, sACN/E1.31 in :mod:`.sacn`) only
differ in how each universe's channel bytes get wrapped into a packet. Both reuse
:class:`DmxLayout` and :class:`DmxSink` so they drive *exactly* the same channels.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

import numpy as np

from .mapping import Mapping

_DMX_MAX = 512


# --- Frame layout ------------------------------------------------------------
@dataclass(frozen=True)
class _UniversePlan:
    """Vectorised write plan for one universe.

    Each entry writes one RGB *component*: colour ``rows[i]``'s component
    ``comps[i]`` (0=R,1=G,2=B) goes to 0-based DMX ``channels[i]``.
    """

    universe: int
    rows: np.ndarray      # (k,) int: source colour-buffer row
    comps: np.ndarray     # (k,) int: which of R/G/B (0/1/2)
    channels: np.ndarray  # (k,) int: 0-based DMX channel within this universe
    length: int           # DMX data length (even, covers the highest channel used)


@dataclass(frozen=True)
class StraddlingPixel:
    fixture: str
    pixel: int          # index within the fixture
    universes: tuple[int, ...]


class DmxLayout:
    """Precomputed mapping from a colour buffer to per-universe DMX channel bytes.

    Channels form a flat, continuous address space that rolls over to the next
    universe past 512, so a fixture can span universes. Each RGB component is
    addressed by its flat channel; pixels whose R/G/B fall in different universes
    are recorded in :attr:`straddling`. Built once from a :class:`Mapping`.
    ``n_leds`` is the colour-buffer length, ordered by ``mapping.output_order()``.
    """

    def __init__(self, mapping: Mapping) -> None:
        fixtures = mapping.output_order()  # canonical pixel order (shared with the model)
        rows: dict[int, list[int]] = {}
        comps: dict[int, list[int]] = {}
        chans: dict[int, list[int]] = {}
        maxchan: dict[int, int] = {}  # 0-based highest channel used per universe
        slices: dict[str, tuple[int, int]] = {}
        straddling: list[StraddlingPixel] = []

        buf_index = 0
        for f in fixtures:
            a = f.raw.artnet
            base = a.universe * _DMX_MAX + (a.start_channel - 1)  # flat 0-based of channel 1
            start = buf_index
            for px, off in enumerate(f.raw.channel_offsets):
                flat_r = base + (off - 1)
                px_unis: set[int] = set()
                for comp in range(3):  # R, G, B
                    flat = flat_r + comp
                    uni, ch = divmod(flat, _DMX_MAX)
                    rows.setdefault(uni, []).append(buf_index)
                    comps.setdefault(uni, []).append(comp)
                    chans.setdefault(uni, []).append(ch)
                    maxchan[uni] = max(maxchan.get(uni, 0), ch)
                    px_unis.add(uni)
                if len(px_unis) > 1:  # this pixel's R/G/B span >1 universe
                    straddling.append(StraddlingPixel(f.raw.name, px, tuple(sorted(px_unis))))
                buf_index += 1
            slices[f.raw.name] = (start, buf_index - start)

        self.n_leds = buf_index
        self.fixture_slices = slices
        self.straddling: tuple[StraddlingPixel, ...] = tuple(straddling)
        self.plans: tuple[_UniversePlan, ...] = tuple(
            _UniversePlan(
                universe=uni,
                rows=np.asarray(rows[uni], dtype=np.int32),
                comps=np.asarray(comps[uni], dtype=np.int32),
                channels=np.asarray(chans[uni], dtype=np.int32),
                length=(maxchan[uni] + 1) + ((maxchan[uni] + 1) & 1),  # +1 to count, round up to even
            )
            for uni in sorted(rows)
        )

    @property
    def universes(self) -> tuple[int, ...]:
        return tuple(p.universe for p in self.plans)


def encode(colors: np.ndarray, gamma: float, brightness: float) -> np.ndarray:
    """Float RGB [0,1] -> gamma-corrected uint8, with a master brightness."""
    c = np.clip(np.asarray(colors, dtype=np.float32), 0.0, 1.0)
    if gamma != 1.0:
        c = c ** gamma
    return (c * (255.0 * float(brightness)) + 0.5).astype(np.uint8)


# --- Sink base ---------------------------------------------------------------
class DmxSink:
    """Packs colour frames into per-universe DMX and sends them over UDP.

    Subclasses set :attr:`PORT` and implement :meth:`_packet` to wrap a universe's
    channel bytes in their wire protocol (ArtDMX / E1.31).
    """

    PORT = 0

    def __init__(
        self,
        mapping: Mapping,
        host: str,
        port: int | None = None,
        *,
        gamma: float = 2.2,
        brightness: float = 1.0,
        sock: socket.socket | None = None,
    ) -> None:
        self.layout = DmxLayout(mapping)
        self.host = host
        self.port = port or self.PORT
        self.gamma = gamma
        self.brightness = brightness
        self._seq: dict[int, int] = {}
        self._owns_sock = sock is None
        self._sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if host.endswith(".255") or host == "255.255.255.255":
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    @property
    def n_leds(self) -> int:
        return self.layout.n_leds

    def _next_seq(self, universe: int) -> int:
        v = self._seq.get(universe, 0) % 255 + 1  # cycle 1..255 (0 = disabled in sACN)
        self._seq[universe] = v
        return v

    def _payloads(self, colors: np.ndarray) -> dict[int, bytes]:
        """Per-universe raw DMX channel bytes (no protocol wrapper, no start code)."""
        colors = np.asarray(colors, dtype=np.float32)
        if colors.shape != (self.layout.n_leds, 3):
            raise ValueError(f"colors must be ({self.layout.n_leds}, 3), got {tuple(colors.shape)}")
        rgb8 = encode(colors, self.gamma, self.brightness)
        out: dict[int, bytes] = {}
        for p in self.layout.plans:
            buf = np.zeros(p.length, dtype=np.uint8)
            buf[p.channels] = rgb8[p.rows, p.comps]
            out[p.universe] = buf.tobytes()
        return out

    def _packet(self, universe: int, dmx_bytes: bytes, sequence: int) -> bytes:
        raise NotImplementedError

    def pack(self, colors: np.ndarray) -> dict[int, bytes]:
        """Return ``{universe: packet_bytes}`` for one colour frame (pure, no I/O)."""
        return {
            uni: self._packet(uni, payload, self._next_seq(uni))
            for uni, payload in self._payloads(colors).items()
        }

    def send_frame(self, colors: np.ndarray) -> int:
        """Pack and send one frame; returns the number of universes sent."""
        packets = self.pack(colors)
        for packet in packets.values():
            self._sock.sendto(packet, (self.host, self.port))
        return len(packets)

    def blackout(self) -> None:
        self.send_frame(np.zeros((self.layout.n_leds, 3), dtype=np.float32))

    def close(self) -> None:
        if self._owns_sock:
            self._sock.close()

    def __enter__(self) -> "DmxSink":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def run_test_pattern(self, duration: float = 5.0, fps: float = 30.0) -> int:
        """Send a moving rainbow for ``duration`` s, then blackout.

        Time-boxed and self-terminating so it can never hang a bring-up session.
        """
        import colorsys
        import os
        import threading
        import time

        n = self.layout.n_leds
        threading.Timer(duration + 5.0, lambda: os._exit(0)).start()  # hard failsafe

        frames = 0
        period = 1.0 / fps
        t0 = time.monotonic()
        ramp = np.arange(n, dtype=np.float32) / max(1, n)
        try:
            while True:
                t = time.monotonic() - t0
                if t >= duration:
                    break
                hue = (ramp + t * 0.25) % 1.0
                rgb = np.array([colorsys.hsv_to_rgb(float(h), 1.0, 1.0) for h in hue],
                               dtype=np.float32)
                self.send_frame(rgb)
                frames += 1
                time.sleep(period)
        finally:
            self.blackout()
        return frames
