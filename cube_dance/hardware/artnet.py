"""ArtNet output sink (Phase 2).

Turn a frame of per-LED colours into ArtNet (ArtDMX) packets and push them onto
the wire. This is the only piece that talks to the lighting network; everything
upstream stays in float-RGB land.

The sink's input contract is a ``(n_leds, 3)`` float array in ``[0, 1]``, ordered
by :class:`ArtnetLayout` -- addressable fixtures sorted by ``(universe,
startChannel)``, pixels in channel-offset order. Phase 3's ``HardwareCubeModel``
will produce its colour buffer in exactly this order; until then any synthetic
frame of the right length drives it (see :meth:`ArtNetSink.run_test_pattern`).

Addressing math, from the MadMapper file: a fixture has a 1-based
``start_channel`` within its universe, and ``channel_offsets[i]`` is the 1-based
offset of pixel ``i``'s **R** channel within the strip (G = +1, B = +2). So the
absolute 1-based R channel is ``start_channel + offset - 1``.

Channels form a **flat, continuous address space** that rolls over to the next
universe past 512 -- a single fixture can span universes (e.g. ``CRight-diag-left-1``
sits in universe 0 ch 496-512 then universe 1 ch 1-37). We therefore address each
RGB *component* by its flat channel and place it in whichever universe it lands
in. The file declares ``avoidCrossUniversePixels``, but the raw channel numbers
don't always honour it; any pixel whose R/G/B fall in different universes is
recorded in :attr:`ArtnetLayout.straddling` so it can be confirmed against the
real controller rather than silently mis-driven.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

import numpy as np

from .mapping import Mapping, build_mapping

ARTNET_PORT = 6454
_DMX_MAX = 512
_OP_DMX = 0x5000
_PROTO_VER = 14


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
    length: int           # DMX data length to send (even, covers the highest channel used)


@dataclass(frozen=True)
class StraddlingPixel:
    fixture: str
    pixel: int          # index within the fixture
    universes: tuple[int, ...]


class ArtnetLayout:
    """Precomputed mapping from a colour buffer to per-universe DMX bytes.

    Built once from a :class:`Mapping`; cheap to keep around. ``n_leds`` is the
    length of the colour buffer the layout (and sink) expect, ordered by
    addressable fixture (sorted by universe, start channel) then pixel.
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


# --- Packet building ---------------------------------------------------------
def build_artdmx(universe: int, data: bytes, sequence: int = 0, physical: int = 0) -> bytes:
    """Assemble one ArtDMX packet. ``data`` is the DMX channel bytes (<=512)."""
    length = len(data)
    if length > _DMX_MAX:
        raise ValueError(f"DMX data {length} > {_DMX_MAX}")
    if length % 2:  # ArtNet length must be even
        data = data + b"\x00"
        length += 1
    return b"".join((
        b"Art-Net\x00",
        _OP_DMX.to_bytes(2, "little"),     # OpCode (lo, hi)
        _PROTO_VER.to_bytes(2, "big"),     # ProtVerHi, ProtVerLo
        bytes((sequence & 0xFF, physical & 0xFF)),
        bytes((universe & 0xFF, (universe >> 8) & 0x7F)),  # SubUni, Net
        length.to_bytes(2, "big"),         # LengthHi, LengthLo
        data,
    ))


def _encode(colors: np.ndarray, gamma: float, brightness: float) -> np.ndarray:
    """Float RGB [0,1] -> gamma-corrected uint8, with a master brightness."""
    c = np.clip(np.asarray(colors, dtype=np.float32), 0.0, 1.0)
    if gamma != 1.0:
        c = c ** gamma
    return (c * (255.0 * float(brightness)) + 0.5).astype(np.uint8)


# --- The sink ----------------------------------------------------------------
class ArtNetSink:
    """Packs colour frames to ArtDMX and sends them over UDP.

    ``host`` is the controller's IP (or a broadcast address like
    ``10.0.0.255`` / ``255.255.255.255``, which enables UDP broadcast).
    """

    def __init__(
        self,
        mapping: Mapping,
        host: str,
        port: int = ARTNET_PORT,
        *,
        gamma: float = 2.2,
        brightness: float = 1.0,
        sock: socket.socket | None = None,
    ) -> None:
        self.layout = ArtnetLayout(mapping)
        self.host = host
        self.port = port
        self.gamma = gamma
        self.brightness = brightness
        self._seq = 0
        self._owns_sock = sock is None
        self._sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if host.endswith(".255") or host == "255.255.255.255":
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    @property
    def n_leds(self) -> int:
        return self.layout.n_leds

    def pack(self, colors: np.ndarray) -> dict[int, bytes]:
        """Return ``{universe: artdmx_packet_bytes}`` for one colour frame.

        Pure: no I/O, deterministic given the sequence counter. Useful for tests.
        """
        colors = np.asarray(colors, dtype=np.float32)
        if colors.shape != (self.layout.n_leds, 3):
            raise ValueError(
                f"colors must be ({self.layout.n_leds}, 3), got {tuple(colors.shape)}"
            )
        rgb8 = _encode(colors, self.gamma, self.brightness)
        self._seq = self._seq % 255 + 1  # ArtNet sequence cycles 1..255 (0 = disabled)
        packets: dict[int, bytes] = {}
        for p in self.layout.plans:
            buf = np.zeros(p.length, dtype=np.uint8)
            buf[p.channels] = rgb8[p.rows, p.comps]
            packets[p.universe] = build_artdmx(p.universe, buf.tobytes(), self._seq)
        return packets

    def send_frame(self, colors: np.ndarray) -> int:
        """Pack and send one frame; returns the number of universes sent."""
        packets = self.pack(colors)
        for packet in packets.values():
            self._sock.sendto(packet, (self.host, self.port))
        return len(packets)

    def blackout(self) -> None:
        """Send an all-off frame (e.g. on shutdown)."""
        self.send_frame(np.zeros((self.layout.n_leds, 3), dtype=np.float32))

    def close(self) -> None:
        if self._owns_sock:
            self._sock.close()

    def __enter__(self) -> "ArtNetSink":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- Hardware bring-up helper -------------------------------------------
    def run_test_pattern(self, duration: float = 5.0, fps: float = 30.0) -> int:
        """Send a moving rainbow for ``duration`` seconds, then blackout.

        Time-boxed and self-terminating so it can never hang a bring-up session.
        Returns the number of frames sent.
        """
        import colorsys
        import os
        import threading
        import time

        n = self.layout.n_leds
        # Hard failsafe: guarantee the process can't be wedged by this call.
        threading.Timer(duration + 5.0, lambda: os._exit(0)).start()

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


def make_sink(host: str, *, config_path: str | None = None, **kwargs) -> ArtNetSink:
    """Convenience: build the default mapping and an ArtNetSink for ``host``."""
    return ArtNetSink(build_mapping(config_path=config_path), host, **kwargs)
