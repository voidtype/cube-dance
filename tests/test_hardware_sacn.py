"""Tests for the sACN/E1.31 output sink: packet structure, channels, loopback."""

from __future__ import annotations

import json
import socket
import struct

import numpy as np
import pytest

from cube_dance.hardware.artnet import ArtNetSink
from cube_dance.hardware.mapping import build_mapping
from cube_dance.hardware.sacn import (
    SACN_PORT,
    build_e131,
    make_sacn_sink,
    sACNSink,
    sacn_multicast_host,
)


def _inventory(tmp_path):
    data = {
        "summary": {},
        "fixtures": [
            {
                "name": "A", "ledCount": 2, "cubeSection": "vertical_left",
                "artnet": {"universe": 1, "startChannel": 1, "endChannel": 6, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
            {
                "name": "B", "ledCount": 2, "cubeSection": "vertical_right",
                "artnet": {"universe": 1, "startChannel": 7, "endChannel": 12, "channelCount": 6},
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
def test_build_e131_layers_and_length():
    data = bytes(range(12))
    pkt = build_e131(universe=1, data=data, sequence=5)
    # Root layer.
    assert pkt[0:2] == b"\x00\x10"            # preamble size
    assert pkt[2:4] == b"\x00\x00"            # post-amble size
    assert pkt[4:16] == b"ASC-E1.17\x00\x00\x00"
    assert struct.unpack(">I", pkt[18:22])[0] == 0x04  # root vector
    # Framing layer (root header is 38 bytes).
    assert struct.unpack(">I", pkt[40:44])[0] == 0x02  # framing vector
    assert pkt[44:108].rstrip(b"\x00") == b"Cube Dance"  # source name
    assert pkt[108] == 100                    # priority
    assert pkt[111] == 5                      # sequence
    assert struct.unpack(">H", pkt[113:115])[0] == 1   # universe
    # DMP layer.
    assert pkt[117] == 0x02                   # DMP vector (set property)
    assert struct.unpack(">H", pkt[123:125])[0] == len(data) + 1  # property count (start code + chans)
    assert pkt[125] == 0x00                   # DMX start code
    assert pkt[126:] == data                  # channel data follows


def test_build_e131_full_universe_is_638_bytes():
    assert len(build_e131(1, bytes(512))) == 638


def test_build_e131_rejects_oversize():
    with pytest.raises(ValueError):
        build_e131(1, bytes(513))


# --- Channel placement -------------------------------------------------------
def test_sacn_places_rgb_at_correct_channels(tmp_path):
    sink = sACNSink(_inventory(tmp_path), host="127.0.0.1", gamma=1.0)
    colors = np.array([
        [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 1.0],
    ], dtype=np.float32)
    pkt = sink.pack(colors)[1]   # universe 1
    dmx = pkt[126:]              # channel data after the 126-byte E1.31 header
    assert list(dmx[0:3]) == [255, 0, 0]
    assert list(dmx[3:6]) == [0, 255, 0]
    assert list(dmx[6:9]) == [0, 0, 255]
    assert list(dmx[9:12]) == [255, 255, 255]


def test_sacn_sequence_per_universe(tmp_path):
    sink = sACNSink(_inventory(tmp_path), host="127.0.0.1")
    c = np.zeros((4, 3), dtype=np.float32)
    seqs = [sink.pack(c)[1][111] for _ in range(3)]
    assert seqs == [1, 2, 3]


def test_universe_offset_applied(tmp_path):
    sink = sACNSink(_inventory(tmp_path), host="127.0.0.1", universe_offset=10)
    pkt = sink.pack(np.zeros((4, 3), dtype=np.float32))[1]
    assert struct.unpack(">H", pkt[113:115])[0] == 11  # 1 + offset 10


def test_warns_on_universe_zero(tmp_path):
    data = {
        "summary": {},
        "fixtures": [{
            "name": "Z", "ledCount": 1, "cubeSection": "vertical_left",
            "artnet": {"universe": 0, "startChannel": 1, "endChannel": 3, "channelCount": 3},
            "pixelMapping": {"channelOffsets": [1]},
        }],
        "structuralFixtures": [],
    }
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps(data))
    cfg = tmp_path / "map.toml"
    cfg.write_text('[[rule]]\nsection="vertical_left"\nkind="edge"\nenabled=true\n')
    with pytest.warns(UserWarning, match="universe"):
        sACNSink(build_mapping(inv, cfg), host="127.0.0.1")


def test_multicast_host():
    assert sacn_multicast_host(1) == "239.255.0.1"
    assert sacn_multicast_host(0x0103) == "239.255.1.3"


# --- ArtNet and sACN drive identical channels --------------------------------
def test_artnet_and_sacn_drive_same_channels(tmp_path):
    mapping = _inventory(tmp_path)
    art = ArtNetSink(mapping, host="127.0.0.1", gamma=1.0)
    sac = sACNSink(mapping, host="127.0.0.1", gamma=1.0)
    colors = np.random.default_rng(0).random((4, 3)).astype(np.float32)
    # Same underlying DMX channel bytes, just different wrappers.
    art_dmx = art._payloads(colors)
    sac_dmx = sac._payloads(colors)
    assert art_dmx.keys() == sac_dmx.keys()
    for uni in art_dmx:
        assert art_dmx[uni] == sac_dmx[uni]


# --- Real UDP loopback -------------------------------------------------------
def test_send_frame_over_udp_loopback(tmp_path):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(2.0)
    port = rx.getsockname()[1]

    sink = sACNSink(_inventory(tmp_path), host="127.0.0.1", port=port, gamma=1.0)
    colors = np.zeros((4, 3), dtype=np.float32)
    colors[2] = [0.0, 0.0, 1.0]  # B px0 -> channels 7..9
    try:
        sent = sink.send_frame(colors)
        assert sent == 1
        packet, _ = rx.recvfrom(2048)
    finally:
        sink.close()
        rx.close()

    assert packet[4:16] == b"ASC-E1.17\x00\x00\x00"
    assert list(packet[126:][6:9]) == [0, 0, 255]


def test_shipped_mapping_builds_sacn_sink():
    sink = make_sacn_sink("127.0.0.1", universe_offset=1)  # +1 to keep all universes >=1
    assert sink.n_leds > 9000  # full cube (real corners/accents + synthesised beams)
    assert SACN_PORT == 5568
    packets = sink.pack(np.full((sink.n_leds, 3), 0.3, dtype=np.float32))
    assert all(len(p) <= 638 for p in packets.values())
    sink.close()
