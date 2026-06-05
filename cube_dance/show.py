"""DUSTLIGHT — a self-running *show*: the seven acts of the night as a director
that crossfades the four mixer decks from dusk to sunrise.

The night is one continuous build-and-release (see ``docs/the-rave.md``). A
:class:`RaveShow` owns a :class:`~cube_dance.visuals.engine.mixer.DeckMixer` and,
each frame, drives its deck presets, deck volumes and global intensity so the
cube *lives the shape of the night* on its own — quiet and warm at arrival,
relentless at peak, fracturing at the deepest hour, then glowing the dawn back
at the sun. A human can still grab the F1 at any time and steer.

The whole arc is compressed into ``duration`` seconds and loops, so the
simulator can demonstrate dusk→sunrise in a few minutes; a real event runs it
across the real hours (set ``duration`` to the night length) or the operator
scrubs acts by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Acts — keyframes of the night. Each names up to four deck presets (None = an
# unused deck this act), the target deck volumes (the F1 faders), a global
# intensity (0..1, brightness + drives each deck's first "intensity"-style knob)
# and whether SYNC (whole-rig kick pump) is engaged.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Act:
    name: str
    clock: str  # the wall-clock time it evokes (for the UI / storyboard)
    presets: tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
    volumes: tuple[float, float, float, float]
    intensity: float
    sync: bool = False
    note: str = ""


# The seven acts, in order. Centre-stage (deck 0) preset is the act's "spine".
DUSTLIGHT: tuple[Act, ...] = (
    Act("Arrival", "6–8pm",
        ("ember", "dust", None, None), (0.55, 0.30, 0.0, 0.0),
        intensity=0.32, note="a low warm body, barely breathing; embers drift in the bush dark"),
    Act("Settling", "8–10pm",
        ("deep", "minimal", "ember", None), (0.72, 0.42, 0.34, 0.0),
        intensity=0.50, note="the floor finds itself: bass corners, soft spectrum, slow sweeps"),
    Act("The Build", "10pm–12",
        ("deep", "punchy", "spiral", None), (0.70, 0.55, 0.42, 0.0),
        intensity=0.70, note="shoulders drop, eyes close: spectrum climbs, the vortex opens"),
    Act("Peak", "12–3am",
        ("punchy", "strobe", "siren", "monolith"), (0.85, 0.60, 0.48, 0.66),
        intensity=1.00, sync=True, note="full lock-in, dust in the lights, hands up — blinders on the drops"),
    Act("Deep Trip", "3–5am",
        ("plasma", "mandelbox", "hypercube", "matrix"), (0.80, 0.58, 0.50, 0.44),
        intensity=0.82, note="eyes-closed sway, the mind-melt: plasma, fractals, the folding cube"),
    Act("Before Light", "5–6am",
        ("aurora", "clouds", "ripple", "sun"), (0.76, 0.52, 0.46, 0.40),
        intensity=0.68, note="the indigo hour, someone crying happy: soft and huge"),
    Act("Sunrise", "6–7am+",
        ("sunrise", "sun", "cymatics", "ember"), (0.86, 0.50, 0.40, 0.46),
        intensity=0.88, note="survivors facing east: the cube glows the dawn back at the sun"),
)


# Registry of named shows (room to grow beyond DUSTLIGHT).
SHOWS: dict[str, tuple[Act, ...]] = {"dustlight": DUSTLIGHT}
_ALIASES = {"dustlight": "dustlight", "dust": "dustlight", "rave": "dustlight",
            "night": "dustlight", "therave": "dustlight"}


def build_show(mixer, name: str, minutes: float = 2.5) -> "RaveShow":
    """Resolve a show ``name`` to a :class:`RaveShow` over ``minutes`` (looping).

    Raises ValueError on an unknown name (the CLI surfaces the available list).
    """
    key = (name or "").strip().lower().replace(" ", "")
    key = _ALIASES.get(key, key)
    acts = SHOWS.get(key)
    if acts is None:
        avail = ", ".join(sorted(SHOWS))
        raise ValueError(f"Unknown show {name!r}. Available: {avail}")
    return RaveShow(mixer, acts=acts, duration=max(1.0, float(minutes) * 60.0))


def _smoothstep(x: float) -> float:
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return x * x * (3.0 - 2.0 * x)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class RaveShow:
    """Director that runs :data:`DUSTLIGHT` over ``duration`` seconds (looping).

    Call :meth:`apply` every frame with the show clock ``t`` (seconds since the
    show started). It rebuilds deck presets only at act boundaries and lerps
    volumes / intensity continuously, so the night is one smooth evolution.
    """

    mixer: object
    acts: tuple[Act, ...] = DUSTLIGHT
    duration: float = 140.0          # seconds for the whole night (loops)
    fade_frac: float = 0.34          # portion of each act used to cross in from the last
    drive_master: bool = True        # the show owns global intensity (master)
    drive_knobs: bool = True         # push intensity into each deck's first intensity knob
    _applied: int = field(default=-1, init=False, repr=False)

    # --- Where are we in the night? -----------------------------------------
    @property
    def n_acts(self) -> int:
        return len(self.acts)

    def phase(self, t: float) -> float:
        """Night position in [0, 1)."""
        if self.duration <= 0:
            return 0.0
        return (t % self.duration) / self.duration

    def locate(self, t: float) -> tuple[int, float]:
        """(act_index, local_phase in [0,1)) for show clock ``t``."""
        p = self.phase(t) * self.n_acts
        ai = int(p) % self.n_acts
        return ai, (p - int(p))

    def act_at(self, t: float) -> Act:
        ai, _ = self.locate(t)
        return self.acts[ai]

    # --- Drive the mixer -----------------------------------------------------
    def _ensure_presets(self, ai: int) -> None:
        """Load the act's presets onto the decks (only the ones that changed)."""
        if ai == self._applied:
            return
        act = self.acts[ai]
        for d, name in enumerate(act.presets):
            if name is None:
                continue  # unused deck this act: leave whatever's loaded (volume 0)
            if self.mixer.preset_name[d] != name:
                self.mixer.set_deck_preset(d, name)
        self._applied = ai

    def apply(self, t: float) -> Act:
        """Advance the show to clock ``t`` and drive the mixer. Returns the act."""
        ai, lp = self.locate(t)
        prev = self.acts[(ai - 1) % self.n_acts]
        cur = self.acts[ai]
        self._ensure_presets(ai)

        a = _smoothstep(lp / self.fade_frac if self.fade_frac > 0 else 1.0)

        for d in range(self.mixer.n_decks):
            changed = prev.presets[d] != cur.presets[d]
            # a deck whose preset just swapped fades up from black (pop-free);
            # a persisting deck lerps straight from its previous volume.
            v0 = 0.0 if changed else prev.volumes[d]
            self.mixer.volumes[d] = _lerp(v0, cur.volumes[d], a)

        if self.drive_master:
            self.mixer.vparams.master = _lerp(prev.intensity, cur.intensity, a)
        self.mixer.vparams.sync_pulse = cur.sync

        if self.drive_knobs:
            inten = _lerp(prev.intensity, cur.intensity, a)
            for d in range(self.mixer.n_decks):
                eng = self.mixer.decks[d]
                spec = getattr(eng, "knob_spec", None)
                if spec and spec[0].effect == "intensity":
                    eng.knob_vals[0] = inten
        return cur
