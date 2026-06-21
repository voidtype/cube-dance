"""sACN / E1.31 output sink — the protocol Luke's Advatek controller expects.

Luke's cube is already configured to receive **sACN** (E1.31), so this is the
preferred output for the real hardware; ArtNet (:mod:`.artnet`) stays as a
fallback. Both share :class:`~cube_dance.hardware.dmx.DmxLayout`, so the exact
same channels are driven either way — only the packet wrapper changes.

E1.31 nests three PDUs (root / framing / DMP). The DMP property values are a DMX
start code (0x00) followed by the channel data, so for a full 512-channel
universe the packet is 638 bytes.

Universe note: E1.31 universes are 1..63999 — universe 0 is reserved. The
MadMapper file uses universes 0..71, so :class:`sACNSink` takes a
``universe_offset`` (and warns if any universe lands below 1). Whether Luke's
Advatek expects the raw numbers or a +1 offset is a one-line setting to confirm
at the integration test.
"""

from __future__ import annotations

import socket
import uuid
import warnings

from .dmx import DmxSink
from .mapping import build_mapping

SACN_PORT = 5568

# Stable component identifier (CID): sACN receivers track a source by its CID, so
# it must be constant across runs. Derived deterministically from a fixed name.
_CID = uuid.uuid5(uuid.NAMESPACE_DNS, "cube-dance.voidtype.cube").bytes
_DEFAULT_SOURCE = "Cube Dance"

_ACN_PID = b"ASC-E1.17\x00\x00\x00"  # 12-byte ACN packet identifier
_VECTOR_ROOT_DATA = 0x00000004
_VECTOR_FRAMING_DATA = 0x00000002
_VECTOR_DMP_SET_PROPERTY = 0x02


def _flags_len(length: int) -> bytes:
    """A 2-byte ACN flags(0x7) + 12-bit PDU length field."""
    return (0x7000 | (length & 0x0FFF)).to_bytes(2, "big")


def build_e131(
    universe: int,
    data: bytes,
    sequence: int = 0,
    *,
    cid: bytes = _CID,
    source_name: str = _DEFAULT_SOURCE,
    priority: int = 100,
) -> bytes:
    """Assemble one E1.31 (sACN) data packet. ``data`` is the DMX channel bytes."""
    n = len(data)
    if n > 512:
        raise ValueError(f"DMX data {n} > 512")

    # DMP layer: start code (0x00) + channel data as property values.
    dmp_len = 11 + n
    dmp = b"".join((
        _flags_len(dmp_len),
        bytes((_VECTOR_DMP_SET_PROPERTY, 0xA1)),  # vector + address/data type
        (0x0000).to_bytes(2, "big"),               # first property address
        (0x0001).to_bytes(2, "big"),               # address increment
        (n + 1).to_bytes(2, "big"),                # property value count (start code + channels)
        b"\x00",                                    # DMX start code
        data,
    ))

    # Framing layer.
    framing_len = 77 + dmp_len
    name = source_name.encode("utf-8")[:63].ljust(64, b"\x00")
    framing = b"".join((
        _flags_len(framing_len),
        _VECTOR_FRAMING_DATA.to_bytes(4, "big"),
        name,
        bytes((priority & 0xFF,)),
        (0).to_bytes(2, "big"),                    # synchronization address
        bytes((sequence & 0xFF, 0x00)),            # sequence + options
        (universe & 0xFFFF).to_bytes(2, "big"),
    ))

    # Root layer.
    root_len = 22 + framing_len
    root = b"".join((
        b"\x00\x10\x00\x00",                       # preamble size + post-amble size
        _ACN_PID,
        _flags_len(root_len),
        _VECTOR_ROOT_DATA.to_bytes(4, "big"),
        cid,
    ))
    return root + framing + dmp


def sacn_multicast_host(universe: int) -> str:
    """The standard E1.31 multicast group for a universe (239.255.<hi>.<lo>)."""
    return f"239.255.{(universe >> 8) & 0xFF}.{universe & 0xFF}"


class sACNSink(DmxSink):
    """Packs colour frames to E1.31 and sends them over UDP (port 5568).

    ``host`` is the controller IP for unicast (matching the ArtNet sink). Pass a
    ``universe_offset`` if the controller's universe numbering differs from the
    MadMapper file's (E1.31 reserves universe 0).
    """

    PORT = SACN_PORT

    def __init__(
        self,
        mapping,
        host: str,
        port: int | None = None,
        *,
        universe_offset: int = 0,
        priority: int = 100,
        source_name: str = _DEFAULT_SOURCE,
        cid: bytes = _CID,
        gamma: float = 2.2,
        brightness: float = 1.0,
        sock: socket.socket | None = None,
    ) -> None:
        super().__init__(mapping, host, port, gamma=gamma, brightness=brightness, sock=sock)
        self.universe_offset = universe_offset
        self.priority = priority
        self.source_name = source_name
        self.cid = cid
        below = [u for u in self.layout.universes if u + universe_offset < 1]
        if below:
            warnings.warn(
                f"sACN universes must be >=1, but {len(below)} land below 1 with "
                f"universe_offset={universe_offset} (e.g. {below[0]}); the controller "
                f"may expect universe_offset=1. Confirm at the integration test.",
                stacklevel=2,
            )

    def _packet(self, universe: int, dmx_bytes: bytes, sequence: int) -> bytes:
        return build_e131(
            universe + self.universe_offset, dmx_bytes, sequence,
            cid=self.cid, source_name=self.source_name, priority=self.priority,
        )


def make_sacn_sink(host: str, *, config_path: str | None = None, **kwargs) -> sACNSink:
    """Convenience: build the default mapping and an sACNSink for ``host``."""
    return sACNSink(build_mapping(config_path=config_path), host, **kwargs)
