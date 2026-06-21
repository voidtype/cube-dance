"""Load + validate the real-hardware fixture mapping (Phase 1).

Two inputs combine into one validated, in-memory :class:`Mapping`:

* **The MadMapper inventory** -- ``reference/led_cube_mapping.json``, extracted
  from Luke's ``.mad`` file. Each fixture carries its ArtNet address (universe +
  DMX channel span), per-pixel channel offsets, an LED count, and a
  ``cubeSection`` tag. Some fixtures carry no addressable LEDs (they're structural
  placeholders), and some almost certainly don't exist on the physical cube --
  Luke left spares in the file.

* **An editable association config** -- ``fixture_map.toml`` (this package, or a
  path you pass). It says, per ``cubeSection`` (with per-fixture overrides), which
  cube-model element a fixture belongs to (``edge`` 0-11 / ``corner`` 0-7) and
  whether it's ``enabled``. This is the remappable layer: swap out mistakes, flip
  unused fixtures off, or wire in new components by editing data -- never code.

Phase 1 deliberately stops at *intent + validation*: it records each fixture's
geometry association and surfaces inconsistencies (channel overlaps, count
mismatches, unmapped fixtures). Binding a fixture to concrete cube-model pixel
indices, and emitting ArtNet, are later phases that consume this structure.

Run it standalone for a report::

    python -m cube_dance.hardware.mapping            # validate the defaults
    python -m cube_dance.hardware.mapping --init     # regenerate a starter config
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# --- Paths -------------------------------------------------------------------
_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parents[1]
DEFAULT_JSON = _REPO_ROOT / "reference" / "led_cube_mapping.json"
DEFAULT_CONFIG = _PKG_DIR / "fixture_map.toml"

# Cube model geometry (see cube_dance/geometry.py): 12 edges, 8 corners.
N_EDGES = 12
N_CORNERS = 8
VALID_KINDS = ("edge", "corner", "none")

_VERTEX_RE = re.compile(r"-(\d+)$")


# --- Parsed MadMapper inventory ---------------------------------------------
@dataclass(frozen=True)
class ArtnetAddress:
    """A fixture's ArtNet/DMX address. Channels are 1-based, inclusive."""

    universe: int
    start_channel: int
    end_channel: int
    channel_count: int


@dataclass(frozen=True)
class RawFixture:
    """One fixture exactly as the MadMapper file describes it (no opinions)."""

    name: str
    led_count: int
    section: str  # the ``cubeSection`` tag
    artnet: ArtnetAddress | None
    channel_offsets: tuple[int, ...]  # 1-based R offset of each pixel within the strip
    structural: bool  # came from ``structuralFixtures`` (expected to carry no LEDs)
    vertex: int | None  # the trailing ``-N`` index, if any (which cube vertex)

    @property
    def has_leds(self) -> bool:
        return self.led_count > 0 and self.artnet is not None


# --- The editable association layer ------------------------------------------
@dataclass(frozen=True)
class RuleSpec:
    """Default association for every fixture in a ``cubeSection``."""

    section: str
    kind: str = "none"
    panel: str | None = None
    enabled: bool = False
    note: str = ""


@dataclass(frozen=True)
class OverrideSpec:
    """Per-fixture override. Any field left ``None`` falls back to the section rule."""

    name: str
    enabled: bool | None = None
    kind: str | None = None
    element_id: int | None = None
    panel: str | None = None
    reverse: bool | None = None
    note: str = ""


@dataclass(frozen=True)
class FixtureMapConfig:
    """The parsed ``fixture_map.toml``: vertex table + section rules + overrides."""

    vertices: dict[int, int] = field(default_factory=dict)
    rules: dict[str, RuleSpec] = field(default_factory=dict)
    overrides: dict[str, OverrideSpec] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    path: Path | None = None

    @classmethod
    def load(cls, path: str | Path | None = None) -> "FixtureMapConfig":
        p = Path(path) if path else DEFAULT_CONFIG
        with open(p, "rb") as fh:
            data = tomllib.load(fh)
        vertices = {int(k): int(v) for k, v in data.get("vertices", {}).items()}
        rules = {}
        for r in data.get("rule", []):
            spec = RuleSpec(
                section=r["section"],
                kind=r.get("kind", "none"),
                panel=r.get("panel"),
                enabled=bool(r.get("enabled", False)),
                note=r.get("note", ""),
            )
            rules[spec.section] = spec
        overrides = {}
        for o in data.get("fixture", []):
            spec = OverrideSpec(
                name=o["name"],
                enabled=o.get("enabled"),
                kind=o.get("kind"),
                element_id=o.get("element_id"),
                panel=o.get("panel"),
                reverse=o.get("reverse"),
                note=o.get("note", ""),
            )
            overrides[spec.name] = spec
        return cls(vertices=vertices, rules=rules, overrides=overrides,
                   meta=data.get("meta", {}), path=p)


# --- The resolved association + the fixture carrying it ----------------------
@dataclass(frozen=True)
class Association:
    """A fixture's place in the cube model, resolved from config.

    ``element_id`` is concrete for corners (looked up from the vertex table) and
    left ``None`` for edges in Phase 1 -- the edge<->fixture index binding is a
    later phase; ``kind``/``panel``/``vertex`` capture the intent until then.
    """

    kind: str  # "edge" | "corner" | "none"
    element_id: int | None
    panel: str | None
    reverse: bool
    source: str  # where the decision came from: rule:<section> / override:<name> / unmatched


@dataclass(frozen=True)
class MappedFixture:
    raw: RawFixture
    enabled: bool
    assoc: Association

    @property
    def addressable(self) -> bool:
        """Enabled *and* actually carrying drivable LEDs."""
        return self.enabled and self.raw.has_leds


@dataclass(frozen=True)
class Mapping:
    """The whole resolved mapping plus where it came from."""

    fixtures: tuple[MappedFixture, ...]
    config: FixtureMapConfig
    json_path: Path
    source_summary: dict = field(default_factory=dict)

    @property
    def addressable(self) -> tuple[MappedFixture, ...]:
        return tuple(f for f in self.fixtures if f.addressable)

    def total_leds(self) -> int:
        return sum(f.raw.led_count for f in self.addressable)

    def output_order(self) -> tuple[MappedFixture, ...]:
        """Addressable fixtures in the canonical output order.

        The single source of truth for pixel ordering: both the ArtNet layout and
        the HardwareCubeModel iterate this so colour-buffer row ``i`` always maps
        to the same physical LED. Sorted by (universe, start channel); pixels
        within a fixture follow its ``channel_offsets`` order.
        """
        return tuple(sorted(
            self.addressable,
            key=lambda f: (f.raw.artnet.universe, f.raw.artnet.start_channel),
        ))


# --- Loading -----------------------------------------------------------------
def _parse_vertex(name: str) -> int | None:
    m = _VERTEX_RE.search(name)
    return int(m.group(1)) if m else None


def _parse_artnet(block: dict | None) -> ArtnetAddress | None:
    if not block:
        return None
    cc = int(block.get("channelCount", 0))
    if cc <= 0:
        return None
    return ArtnetAddress(
        universe=int(block["universe"]),
        start_channel=int(block["startChannel"]),
        end_channel=int(block["endChannel"]),
        channel_count=cc,
    )


def _raw_from_entry(entry: dict, *, structural: bool) -> RawFixture:
    offsets = tuple(int(o) for o in entry.get("pixelMapping", {}).get("channelOffsets", []))
    return RawFixture(
        name=entry["name"],
        led_count=int(entry.get("ledCount", 0)),
        section=entry.get("cubeSection", ""),
        artnet=_parse_artnet(entry.get("artnet")),
        channel_offsets=offsets,
        structural=structural,
        vertex=_parse_vertex(entry["name"]),
    )


def load_madmapper(json_path: str | Path | None = None) -> list[RawFixture]:
    """Parse every fixture (light-bearing + structural) from the MadMapper JSON."""
    p = Path(json_path) if json_path else DEFAULT_JSON
    data = json.loads(Path(p).read_text())
    raws = [_raw_from_entry(e, structural=False) for e in data.get("fixtures", [])]
    raws += [_raw_from_entry(e, structural=True) for e in data.get("structuralFixtures", [])]
    return raws


def resolve(raw: RawFixture, config: FixtureMapConfig) -> MappedFixture:
    """Apply the section rule then any per-fixture override to one fixture."""
    rule = config.rules.get(raw.section)
    if rule is not None:
        enabled, kind, panel = rule.enabled, rule.kind, rule.panel
        source = f"rule:{raw.section}"
    else:
        enabled, kind, panel = False, "none", None
        source = "unmatched"
    reverse = False
    element_id: int | None = None

    ov = config.overrides.get(raw.name)
    if ov is not None:
        if ov.enabled is not None:
            enabled = ov.enabled
        if ov.kind is not None:
            kind = ov.kind
        if ov.panel is not None:
            panel = ov.panel
        if ov.reverse is not None:
            reverse = ov.reverse
        source = f"override:{raw.name}"

    # Corners get a concrete id from the (editable) vertex table; edges wait for
    # the Phase-3 binder. An explicit override id always wins.
    if kind == "corner" and raw.vertex is not None:
        element_id = config.vertices.get(raw.vertex)
    if ov is not None and ov.element_id is not None:
        element_id = ov.element_id

    return MappedFixture(raw, enabled, Association(kind, element_id, panel, reverse, source))


def build_mapping(
    json_path: str | Path | None = None,
    config_path: str | Path | None = None,
) -> Mapping:
    """Load both inputs and resolve the association for every fixture."""
    p = Path(json_path) if json_path else DEFAULT_JSON
    raws = load_madmapper(p)
    config = FixtureMapConfig.load(config_path)
    fixtures = tuple(resolve(r, config) for r in raws)
    summary = json.loads(Path(p).read_text()).get("summary", {})
    return Mapping(fixtures=fixtures, config=config, json_path=Path(p), source_summary=summary)


# --- Validation --------------------------------------------------------------
@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warn" | "info"
    code: str
    message: str


def validate(mapping: Mapping) -> list[Issue]:
    """Surface every inconsistency between intent, config, and the hardware data."""
    issues: list[Issue] = []
    add = issues.append

    for f in mapping.fixtures:
        r, a = f.raw, f.assoc

        if a.kind not in VALID_KINDS:
            add(Issue("error", "bad-kind", f"{r.name}: unknown kind {a.kind!r}"))
        if a.source == "unmatched":
            add(Issue("warn", "unmatched",
                      f"{r.name}: section {r.section!r} has no rule -> disabled by default"))

        # Per-pixel offsets must describe exactly the declared LEDs.
        if r.has_leds and len(r.channel_offsets) != r.led_count:
            add(Issue("error", "offset-count",
                      f"{r.name}: {len(r.channel_offsets)} channel offsets != {r.led_count} LEDs"))

        if f.enabled and a.kind == "none":
            add(Issue("warn", "enabled-no-target",
                      f"{r.name}: enabled but has no geometry target (kind=none)"))
        if f.enabled and not r.has_leds:
            add(Issue("info", "enabled-no-leds",
                      f"{r.name}: enabled but carries no addressable LEDs "
                      f"(structural/placeholder) -- supply ArtNet data to drive it"))
        if a.kind == "corner" and r.vertex is not None and a.element_id is None:
            add(Issue("warn", "vertex-unmapped",
                      f"{r.name}: vertex {r.vertex} missing from [vertices] table"))
        if a.element_id is not None:
            limit = N_EDGES if a.kind == "edge" else N_CORNERS
            if not (0 <= a.element_id < limit):
                add(Issue("error", "id-range",
                          f"{r.name}: {a.kind} id {a.element_id} out of range 0..{limit - 1}"))

    # DMX channel collisions within a universe (addressable fixtures only).
    by_universe: dict[int, list[MappedFixture]] = {}
    for f in mapping.addressable:
        by_universe.setdefault(f.raw.artnet.universe, []).append(f)
    for uni, fixtures in by_universe.items():
        spans = sorted(fixtures, key=lambda f: f.raw.artnet.start_channel)
        for prev, cur in zip(spans, spans[1:]):
            if cur.raw.artnet.start_channel <= prev.raw.artnet.end_channel:
                add(Issue("error", "channel-overlap",
                          f"universe {uni}: {cur.raw.name} "
                          f"(ch {cur.raw.artnet.start_channel}-{cur.raw.artnet.end_channel}) "
                          f"overlaps {prev.raw.name} "
                          f"(ch {prev.raw.artnet.start_channel}-{prev.raw.artnet.end_channel})"))

    # Reconcile our addressable total against the file's own summary.
    declared = mapping.source_summary.get("totalAddressableLEDs")
    if declared is not None:
        got = sum(f.raw.led_count for f in mapping.fixtures if f.raw.has_leds)
        if got != declared:
            add(Issue("info", "led-total",
                      f"file declares {declared} addressable LEDs; parsed {got} "
                      f"(differs only if fixtures changed)"))
    return issues


# --- Reporting + CLI ---------------------------------------------------------
def format_report(mapping: Mapping, issues: list[Issue]) -> str:
    fixtures = mapping.fixtures
    n_light = sum(1 for f in fixtures if not f.raw.structural)
    n_struct = sum(1 for f in fixtures if f.raw.structural)
    n_enabled = sum(1 for f in fixtures if f.enabled)
    n_addr = len(mapping.addressable)

    lines = []
    lines.append(f"MadMapper inventory : {mapping.json_path}")
    lines.append(f"Association config  : {mapping.config.path}")
    lines.append("")
    lines.append(f"fixtures            : {len(fixtures)}  ({n_light} light, {n_struct} structural)")
    lines.append(f"enabled             : {n_enabled}")
    lines.append(f"addressable (driven): {n_addr} fixtures, {mapping.total_leds()} LEDs")
    lines.append("")

    # Per-section breakdown.
    sections: dict[str, list[MappedFixture]] = {}
    for f in fixtures:
        sections.setdefault(f.raw.section, []).append(f)
    lines.append("by cubeSection:")
    for sec in sorted(sections):
        fs = sections[sec]
        en = sum(1 for f in fs if f.enabled)
        leds = sum(f.raw.led_count for f in fs if f.addressable)
        kind = fs[0].assoc.kind
        flag = "on " if en else "off"
        lines.append(f"  [{flag}] {sec:<22} kind={kind:<6} {len(fs):>2} fixtures, "
                     f"{en} enabled, {leds} LEDs")
    lines.append("")

    order = {"error": 0, "warn": 1, "info": 2}
    counts = {s: sum(1 for i in issues if i.severity == s) for s in order}
    lines.append(f"issues: {counts['error']} errors, {counts['warn']} warnings, "
                 f"{counts['info']} info")
    for i in sorted(issues, key=lambda i: order[i.severity]):
        lines.append(f"  [{i.severity:<5}] {i.code}: {i.message}")
    return "\n".join(lines)


def generate_default_config_toml(raws: list[RawFixture]) -> str:
    """Emit a starter ``fixture_map.toml`` from an inventory.

    Best-effort heuristics: corner sections -> ``corner``, vertical/horizontal/
    column sections -> ``edge``; sections that carry real LEDs are enabled, the
    rest start disabled. Hand-edit afterwards -- this is a scaffold, not truth.
    """
    sections: dict[str, list[RawFixture]] = {}
    for r in raws:
        sections.setdefault(r.section, []).append(r)

    def guess_kind(sec: str) -> str:
        if sec.startswith("corner"):
            return "corner"
        if sec.startswith(("vertical", "horizontal", "column")):
            return "edge"
        return "none"

    out = ["[meta]", 'source = "reference/led_cube_mapping.json"', ""]
    out.append("[vertices]")
    for v in range(1, 9):
        out.append(f'"{v}" = {v - 1}')
    out.append("")
    for sec in sorted(sections):
        fs = sections[sec]
        has_leds = any(f.has_leds for f in fs)
        kind = guess_kind(sec)
        out.append("[[rule]]")
        out.append(f'section = "{sec}"')
        out.append(f'kind = "{kind if has_leds else kind}"')
        out.append(f"enabled = {'true' if has_leds and kind != 'none' else 'false'}")
        if not has_leds:
            out.append('note = "no addressable LEDs in this extraction"')
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="cube-dance-map", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=None, help="MadMapper inventory JSON (default: reference/).")
    ap.add_argument("--config", default=None, help="fixture_map.toml (default: packaged).")
    ap.add_argument("--init", action="store_true",
                    help="Print a starter config generated from the inventory and exit.")
    args = ap.parse_args(argv)

    if args.init:
        print(generate_default_config_toml(load_madmapper(args.json)))
        return 0

    mapping = build_mapping(args.json, args.config)
    issues = validate(mapping)
    print(format_report(mapping, issues))
    return 1 if any(i.severity == "error" for i in issues) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
