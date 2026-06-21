"""ArtNet (ArtDMX) output sink.

The ArtNet wire format on top of the protocol-neutral core in :mod:`.dmx`. See
:mod:`.sacn` for the E1.31 sink Luke's Advatek controller is configured for —
they share :class:`~cube_dance.hardware.dmx.DmxLayout`, so both drive identical
channels and differ only in the packet wrapper.

A fixture can span universes (the real ``.mad`` has these); pixels whose R/G/B
fall in different universes are recorded in ``layout.straddling``.
"""

from __future__ import annotations

from .dmx import DmxLayout, DmxSink
from .mapping import build_mapping

ARTNET_PORT = 6454
_DMX_MAX = 512
_OP_DMX = 0x5000
_PROTO_VER = 14

# Backwards-compatible alias: the layout is protocol-neutral but was first
# introduced here. Prefer cube_dance.hardware.dmx.DmxLayout in new code.
ArtnetLayout = DmxLayout


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


class ArtNetSink(DmxSink):
    """Packs colour frames to ArtDMX and sends them over UDP (port 6454)."""

    PORT = ARTNET_PORT

    def _packet(self, universe: int, dmx_bytes: bytes, sequence: int) -> bytes:
        return build_artdmx(universe, dmx_bytes, sequence)


def make_sink(host: str, *, config_path: str | None = None, **kwargs) -> ArtNetSink:
    """Convenience: build the default mapping and an ArtNetSink for ``host``."""
    return ArtNetSink(build_mapping(config_path=config_path), host, **kwargs)
