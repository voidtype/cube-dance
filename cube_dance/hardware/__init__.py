"""Real-hardware mapping + output for the cube.

Phase 1 lives in :mod:`cube_dance.hardware.mapping`: it loads the MadMapper
fixture inventory (``reference/led_cube_mapping.json``) and an *editable* config
file that associates each fixture with the cube model's geometry. The config is
the seam that absorbs reality drift -- disable fixtures Luke left unused, retarget
mistakes, or wire in new components -- all without touching code.

Later phases add the geometry binder (abstract pixels <-> real fixtures) and the
ArtNet output sink. None of that is wired into the live app yet.
"""

from __future__ import annotations

from .artnet import ArtNetSink, ArtnetLayout, build_artdmx, make_sink
from .mapping import (
    Association,
    FixtureMapConfig,
    MappedFixture,
    Mapping,
    RawFixture,
    build_mapping,
    load_madmapper,
)
from .model import HardwareCubeModel, build_hardware_model
from .placement import Placement, place_fixture

__all__ = [
    "Association",
    "ArtNetSink",
    "ArtnetLayout",
    "FixtureMapConfig",
    "HardwareCubeModel",
    "MappedFixture",
    "Mapping",
    "Placement",
    "RawFixture",
    "build_artdmx",
    "build_hardware_model",
    "build_mapping",
    "load_madmapper",
    "make_sink",
    "place_fixture",
]
