"""Tests for the Phase-1 real-hardware fixture mapping loader + validation."""

from __future__ import annotations

import json

import pytest

from cube_dance.hardware import build_mapping, load_madmapper
from cube_dance.hardware.mapping import (
    DEFAULT_JSON,
    FixtureMapConfig,
    Issue,
    RawFixture,
    resolve,
    validate,
)


# --- A tiny synthetic inventory + config, written to tmp files --------------
def _write_inventory(tmp_path):
    data = {
        "summary": {"totalAddressableLEDs": 4},
        "fixtures": [
            {
                "name": "CLeft-top-1", "ledCount": 2, "cubeSection": "corner_left_top",
                "artnet": {"universe": 0, "startChannel": 1, "endChannel": 6, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
            {
                "name": "Left-1", "ledCount": 2, "cubeSection": "vertical_left",
                "artnet": {"universe": 0, "startChannel": 7, "endChannel": 12, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
            {  # a control point we expect to be disabled
                "name": "Channel 6", "ledCount": 1, "cubeSection": "channel",
                "artnet": {"universe": 0, "startChannel": 13, "endChannel": 15, "channelCount": 3},
                "pixelMapping": {"channelOffsets": [1]},
            },
        ],
        "structuralFixtures": [
            {
                "name": "Column-1", "ledCount": 0, "cubeSection": "column",
                "artnet": {"universe": 1, "startChannel": 1, "endChannel": 1, "channelCount": 0},
            },
        ],
    }
    p = tmp_path / "inv.json"
    p.write_text(json.dumps(data))
    return p


def _write_config(tmp_path):
    toml = """
[vertices]
"1" = 0

[[rule]]
section = "corner_left_top"
kind = "corner"
enabled = true

[[rule]]
section = "vertical_left"
kind = "edge"
enabled = true

[[rule]]
section = "channel"
kind = "none"
enabled = false

[[rule]]
section = "column"
kind = "edge"
enabled = false
"""
    p = tmp_path / "map.toml"
    p.write_text(toml)
    return p


def test_load_madmapper_parses_both_lists(tmp_path):
    raws = load_madmapper(_write_inventory(tmp_path))
    assert len(raws) == 4
    by_name = {r.name: r for r in raws}
    assert by_name["CLeft-top-1"].vertex == 1
    assert by_name["CLeft-top-1"].channel_offsets == (1, 4)
    assert by_name["Column-1"].structural is True
    assert by_name["Column-1"].has_leds is False  # no LED data
    assert by_name["CLeft-top-1"].has_leds is True


def test_build_mapping_resolves_and_counts(tmp_path):
    m = build_mapping(_write_inventory(tmp_path), _write_config(tmp_path))
    by_name = {f.raw.name: f for f in m.fixtures}

    # Corner gets a concrete id from the vertex table; edge stays None in Phase 1.
    assert by_name["CLeft-top-1"].assoc.kind == "corner"
    assert by_name["CLeft-top-1"].assoc.element_id == 0
    assert by_name["Left-1"].assoc.kind == "edge"
    assert by_name["Left-1"].assoc.element_id is None

    # Disabled / no-LED fixtures are excluded from the driven set.
    assert by_name["Channel 6"].enabled is False
    assert by_name["Column-1"].addressable is False

    assert {f.raw.name for f in m.addressable} == {"CLeft-top-1", "Left-1"}
    assert m.total_leds() == 4


def test_override_wins_over_section_rule(tmp_path):
    raw = RawFixture(
        name="CLeft-top-1", led_count=2, section="corner_left_top", artnet=None,
        channel_offsets=(1, 4), structural=False, vertex=1,
    )
    cfg = FixtureMapConfig(
        vertices={1: 0},
        rules={"corner_left_top": __import__("cube_dance.hardware.mapping", fromlist=["RuleSpec"]).RuleSpec(
            section="corner_left_top", kind="corner", enabled=True)},
        overrides={"CLeft-top-1": __import__("cube_dance.hardware.mapping", fromlist=["OverrideSpec"]).OverrideSpec(
            name="CLeft-top-1", enabled=False, element_id=5, reverse=True)},
    )
    mf = resolve(raw, cfg)
    assert mf.enabled is False
    assert mf.assoc.element_id == 5
    assert mf.assoc.reverse is True
    assert mf.assoc.source == "override:CLeft-top-1"


def test_validate_flags_channel_overlap_and_offset_mismatch(tmp_path):
    data = {
        "summary": {},
        "fixtures": [
            {
                "name": "A", "ledCount": 2, "cubeSection": "vertical_left",
                "artnet": {"universe": 0, "startChannel": 1, "endChannel": 6, "channelCount": 6},
                "pixelMapping": {"channelOffsets": [1, 4]},
            },
            {  # overlaps A on universe 0, and its offsets don't match ledCount
                "name": "B", "ledCount": 3, "cubeSection": "vertical_right",
                "artnet": {"universe": 0, "startChannel": 5, "endChannel": 10, "channelCount": 6},
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
    m = build_mapping(inv, cfg)
    issues = validate(m)
    codes = {i.code for i in issues}
    assert "channel-overlap" in codes
    assert "offset-count" in codes
    assert any(i.severity == "error" for i in issues)


def test_unmatched_section_disables_and_warns(tmp_path):
    data = {
        "summary": {},
        "fixtures": [{
            "name": "Mystery-9", "ledCount": 1, "cubeSection": "brand_new_thing",
            "artnet": {"universe": 4, "startChannel": 1, "endChannel": 3, "channelCount": 3},
            "pixelMapping": {"channelOffsets": [1]},
        }],
        "structuralFixtures": [],
    }
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps(data))
    cfg = tmp_path / "map.toml"
    cfg.write_text("# empty config\n")
    m = build_mapping(inv, cfg)
    fx = m.fixtures[0]
    assert fx.enabled is False
    assert fx.assoc.source == "unmatched"
    assert any(i.code == "unmatched" for i in validate(m))


# --- The real shipped config must load + validate clean ----------------------
@pytest.mark.skipif(not DEFAULT_JSON.exists(), reason="reference inventory not present")
def test_shipped_config_has_no_errors():
    m = build_mapping()  # packaged fixture_map.toml + reference JSON
    issues = validate(m)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], f"unexpected validation errors: {errors}"
    assert m.total_leds() > 0
    # Sanity: only corner + edge-accent sections are driven today.
    driven_sections = {f.raw.section for f in m.addressable}
    assert driven_sections, "expected some addressable fixtures"
    assert all(s.startswith(("corner_", "vertical_")) for s in driven_sections)
