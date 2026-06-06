"""Python preset modules: each exposes ``build(engine)`` to compose elements.

Presets are code (full expressiveness, the requested element-subscription model).
"""

from __future__ import annotations

import importlib

# Ordered list the deck mixer + browse encoder cycle through. The first four are
# the original mixer-friendly presets (deck defaults); the next four are wilder,
# stylistically distinct "imaginings" of what a preset can be.
PRESET_ORDER = (
    # originals (deck defaults)
    "deep", "punchy", "minimal", "strobe", "inferno", "matrix", "plasma", "siren", "spiral", "vortex",
    # 20 new 3-D effects (see docs/effect-ideas.md)
    "life", "reaction", "flock", "crystal", "clouds", "menger", "bulb", "slice", "sphere", "knot",
    "icosa", "snake", "lacing", "arc", "current", "sun", "ripple", "aurora", "accretion", "dipole",
    # 3-D Mandelbrot cousin + 4-D projection (spectrum-navigated)
    "mandelbox", "hypercube",
    # round 2 — famous-visualisation-inspired (docs/effect-ideas-2.md, part A)
    "scope", "waterfall", "feedback", "radial", "magneto", "cymatics", "tunnel", "larson", "blinder", "panels",
    # round 2 — truss-structure-aware (part B)
    "beambars", "lacingwave", "impulse", "facespin", "barberpole", "build", "rings", "drip", "diagonal", "modal",
    # DUSTLIGHT — the rave show signature presets (docs/the-rave.md)
    "ember", "dust", "monolith", "sunrise",
    # New Year — a 10 -> 1 countdown the cube performs (the START pad), then the bells
    "countdown",
)
BUILTINS = PRESET_ORDER


def load(name: str, engine):
    """Build ``engine`` from preset ``name`` and apply its performance schema.

    A preset module exposes ``build(engine)`` (adds elements) and may declare
    ``KNOBS`` (list of ``Knob``) and ``TRIGGERS`` (list of ``Trigger``) for the
    F1 surface. Raises ValueError if unknown.
    """
    try:
        mod = importlib.import_module(f"cube_dance.presets.{name}")
    except ModuleNotFoundError as exc:
        raise ValueError(f"Unknown preset {name!r} (built-ins: {', '.join(BUILTINS)})") from exc
    if not hasattr(mod, "build"):
        raise ValueError(f"Preset {name!r} has no build(engine)")
    mod.build(engine)
    if hasattr(engine, "set_schema"):
        engine.set_schema(getattr(mod, "KNOBS", None), getattr(mod, "TRIGGERS", None))
    return engine
