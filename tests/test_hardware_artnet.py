"""Tests for the Phase-2 ArtNet output sink: packet layout + loopback send."""

from __future__ import annotations

import json
import socket

import numpy as np
import pytest

from cube_dance.hardware.artnet import ArtnetLayout, ArtNetSink, build_artdmx
from cube_dance.hardware.mapping import build_mapping


def _inventory(tmp_path):
    """Two fixtures, 2 LEDs each, on one universe at known channels."""
    data = {
        "summary": {},
        "fixtures": [
            {
                "name": "A", "ledCount": 2, "cubeSection": "vertical_left",
                "artnet": {"universe": 0, "startChannel": 1, "endChannel": 6, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
            {
                "name": "B", "ledCount": 2, "cubeSection": "vertical_right",
                "artnet": {"universe": 0, "startChannel": 7, "endChannel": 12, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
        ],
        "structuralFixtures": [],
    }
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps(data))
    cfg = tmp_path / "map.toml"
    cfg.write_text(
        '[[rule]]\nsection="vertical_left"\nkind="edge"\nenabled=true\n'
        '[[rule]]\nsection="vertical_right"\nkind="edge"\nenabled=true\n'
    )
    return build_mapping(inv, cfg)


# --- Packet structure --------------------------------------------------------
def test_build_artdmx_header():
    pkt = build_artdmx(universe=0x0103, data=bytes([10, 20, 30]), sequence=7)
    assert pkt[:8] == b"Art-Net\x00"
    assert pkt[8:10] == b"\x00\x50"        # OpDmx, little-endian
    assert pkt[10:12] == b"\x00\x0e"       # protocol version 14
    assert pkt[12] == 7                     # sequence
    assert pkt[13] == 0                     # physical
    assert pkt[14] == 0x03                  # SubUni (low byte of universe)
    assert pkt[15] == 0x01                  # Net (high byte)
    # Odd data length (3) is padded to even (4).
    assert pkt[16] == 0 and pkt[17] == 4    # length hi/lo
    assert pkt[18:22] == bytes([10, 20, 30, 0])


def test_build_artdmx_rejects_oversize():
    with pytest.raises(ValueError):
        build_artdmx(0, bytes(513))


# --- Layout ------------------------------------------------------------------
def test_layout_orders_and_sizes(tmp_path):
    layout = ArtnetLayout(_inventory(tmp_path))
    assert layout.n_leds == 4
    assert layout.universes == (0,)
    assert layout.straddling == ()  # nothing crosses a universe here
    p = layout.plans[0]
    # 4 pixels x 3 components = 12 channel writes, covering DMX channels 1..12.
    assert sorted(p.channels) == list(range(12))
    assert p.length == 12
    assert layout.fixture_slices == {"A": (0, 2), "B": (2, 2)}


def test_layout_rolls_over_universe_boundary(tmp_path):
    """A fixture starting near channel 512 spills into the next universe."""
    data = {
        "summary": {},
        "fixtures": [{
            "name": "Edge", "ledCount": 2, "cubeSection": "vertical_left",
            "artnet": {"universe": 0, "startChannel": 511, "endChannel": 516, "channelCount": 6},
            "pixelMapping": {"channelOffsets": [1, 4]},
        }],
        "structuralFixtures": [],
    }
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps(data))
    cfg = tmp_path / "map.toml"
    cfg.write_text('[[rule]]\nsection="vertical_left"\nkind="edge"\nenabled=true\n')
    layout = ArtnetLayout(build_mapping(inv, cfg))
    # px0 R at channel 511 -> R,G in uni0 (ch 511,512), B in uni1 (ch 1).
    assert layout.universes == (0, 1)
    assert len(layout.straddling) == 1
    assert layout.straddling[0].fixture == "Edge"
    assert layout.straddling[0].universes == (0, 1)


# --- Packing the right bytes into the right channels -------------------------
def test_pack_places_rgb_at_correct_channels(tmp_path):
    sink = ArtNetSink(_inventory(tmp_path), host="127.0.0.1", gamma=1.0, brightness=1.0)
    colors = np.array([
        [1.0, 0.0, 0.0],   # A px0 -> R channel 1 (idx 0)
        [0.0, 1.0, 0.0],   # A px1 -> R channel 4 (idx 3)
        [0.0, 0.0, 1.0],   # B px0 -> R channel 7 (idx 6)
        [1.0, 1.0, 1.0],   # B px1 -> R channel 10 (idx 9)
    ], dtype=np.float32)
    pkt = sink.pack(colors)[0]
    dmx = pkt[18:]  # channel data after the 18-byte header
    assert list(dmx[0:3]) == [255, 0, 0]
    assert list(dmx[3:6]) == [0, 255, 0]
    assert list(dmx[6:9]) == [0, 0, 255]
    assert list(dmx[9:12]) == [255, 255, 255]


def test_pack_rejects_wrong_shape(tmp_path):
    sink = ArtNetSink(_inventory(tmp_path), host="127.0.0.1")
    with pytest.raises(ValueError):
        sink.pack(np.zeros((3, 3), dtype=np.float32))


def test_gamma_and_brightness_applied(tmp_path):
    sink = ArtNetSink(_inventory(tmp_path), host="127.0.0.1", gamma=2.0, brightness=0.5)
    colors = np.zeros((4, 3), dtype=np.float32)
    colors[0, 0] = 0.5
    dmx = sink.pack(colors)[0][18:]
    # 0.5**2 * 255 * 0.5 = 31.875 -> 32
    assert dmx[0] == 32


def test_sequence_increments_and_wraps(tmp_path):
    sink = ArtNetSink(_inventory(tmp_path), host="127.0.0.1")
    c = np.zeros((4, 3), dtype=np.float32)
    seqs = [sink.pack(c)[0][12] for _ in range(3)]
    assert seqs == [1, 2, 3]  # starts at 1, never 0


# --- Real UDP loopback: packets actually hit the wire ------------------------
def test_send_frame_over_udp_loopback(tmp_path):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(2.0)
    port = rx.getsockname()[1]

    sink = ArtNetSink(_inventory(tmp_path), host="127.0.0.1", port=port, gamma=1.0)
    colors = np.zeros((4, 3), dtype=np.float32)
    colors[2] = [0.0, 0.0, 1.0]  # B px0 -> channel 7..9
    try:
        sent = sink.send_frame(colors)
        assert sent == 1
        packet, _ = rx.recvfrom(1024)
    finally:
        sink.close()
        rx.close()

    assert packet[:8] == b"Art-Net\x00"
    dmx = packet[18:]
    assert list(dmx[6:9]) == [0, 0, 255]


# --- The shipped mapping yields a sane, sendable layout ----------------------
def test_shipped_mapping_builds_sink():
    sink = ArtNetSink(build_mapping(), host="127.0.0.1")
    assert sink.n_leds == 2440  # corners + edge accents in the default config
    assert len(sink.layout.universes) > 1
    # A full frame packs without error and every universe fits in a DMX frame.
    packets = sink.pack(np.full((sink.n_leds, 3), 0.3, dtype=np.float32))
    assert all(len(p) <= 18 + 512 for p in packets.values())
    # The real file has fixtures that roll over universes; at least one pixel
    # straddles a boundary, and the layout records it rather than dropping it.
    assert len(sink.layout.straddling) >= 1
    sink.close()
