"""Python preset modules: each exposes ``build(engine)`` to compose elements.

Presets are code (full expressiveness, the requested element-subscription model).
"""

from __future__ import annotations

import importlib

# Ordered list the deck mixer + browse encoder cycle through.
PRESET_ORDER = ("deep", "punchy", "minimal", "strobe")
BUILTINS = PRESET_ORDER


def load(name: str, engine):
    """Build ``engine`` from preset ``name``. Raises ValueError if unknown."""
    try:
        mod = importlib.import_module(f"cube_dance.presets.{name}")
    except ModuleNotFoundError as exc:
        raise ValueError(f"Unknown preset {name!r} (built-ins: {', '.join(BUILTINS)})") from exc
    if not hasattr(mod, "build"):
        raise ValueError(f"Preset {name!r} has no build(engine)")
    mod.build(engine)
    return engine
