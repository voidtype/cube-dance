"""A tasteful terminal countdown to midnight — the Monolith into 2027.

Counts down to New Year's Eve (default 2027-01-01 00:00 local) in big gold
block digits, and names the DUSTLIGHT act the cube would be performing at that
moment of the night. A small companion to showcase/cube-into-2027.html.

    uv run python tools/countdown.py            # live, Ctrl-C to quit
    uv run python tools/countdown.py --once      # print one frame and exit
    uv run python tools/countdown.py --for 5     # run ~5s then exit (failsafe)
    uv run python tools/countdown.py --target 2026-12-31T20:00
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time

GOLD = "\033[38;5;215m"
AMBER = "\033[38;5;208m"
DIM = "\033[38;5;245m"
FAINT = "\033[38;5;238m"
MOON = "\033[38;5;111m"
BOLD = "\033[1m"
RST = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE = "\033[?25l"
SHOW = "\033[?25h"

# 5-row block digits + colon.
_GLYPH = {
    "0": ["█████", "█   █", "█   █", "█   █", "█████"],
    "1": ["  ██ ", " █ █ ", "   █ ", "   █ ", " ████"],
    "2": ["█████", "    █", "█████", "█    ", "█████"],
    "3": ["█████", "    █", " ████", "    █", "█████"],
    "4": ["█   █", "█   █", "█████", "    █", "    █"],
    "5": ["█████", "█    ", "█████", "    █", "█████"],
    "6": ["█████", "█    ", "█████", "█   █", "█████"],
    "7": ["█████", "    █", "   █ ", "  █  ", "  █  "],
    "8": ["█████", "█   █", "█████", "█   █", "█████"],
    "9": ["█████", "█   █", "█████", "    █", "█████"],
    ":": ["     ", "  █  ", "     ", "  █  ", "     "],
    " ": ["     ", "     ", "     ", "     ", "     "],
}

# DUSTLIGHT acts as a fraction of the night (dusk≈18:00 -> sunrise≈07:00),
# so we can name the act the cube is in at the countdown's target moment.
_ACTS = [
    (18.0, "Arrival", "a low warm body, barely breathing"),
    (20.0, "Settling", "the floor finds itself"),
    (22.0, "The Build", "spectrum climbs, the vortex opens"),
    (0.0, "Peak", "the year turns — hands up, blinders on the drop"),
    (3.0, "Deep Trip", "the mind-melt: plasma, fractals, the folding cube"),
    (5.0, "Before Light", "the indigo hour"),
    (6.5, "Sunrise", "the cube glows the dawn back at the sun"),
]


def act_at(when: dt.datetime) -> tuple[str, str]:
    h = when.hour + when.minute / 60.0
    night = h if h >= 18.0 else h + 24.0  # wrap past-midnight onto the dusk timeline
    name, note = _ACTS[0][1], _ACTS[0][2]
    for start, nm, nt in _ACTS:
        s = start if start >= 18.0 else start + 24.0
        if night >= s:
            name, note = nm, nt
    return name, note


def big(text: str, color: str) -> list[str]:
    rows = ["", "", "", "", ""]
    for ch in text:
        g = _GLYPH.get(ch, _GLYPH[" "])
        for i in range(5):
            rows[i] += g[i] + " "
    return [color + r + RST for r in rows]


def frame(target: dt.datetime, now: dt.datetime, width: int = 80) -> str:
    diff = target - now
    secs = int(diff.total_seconds())
    out = []
    pad = lambda s: s.center(width)

    out.append("")
    out.append(pad(f"{GOLD}{BOLD}D U S T L I G H T{RST}"))
    out.append(pad(f"{DIM}the Monolith crosses into 2027{RST}"))
    out.append("")

    if secs <= 0:
        for line in big("2027", GOLD):
            out.append(pad(line))
        out.append("")
        out.append(pad(f"{AMBER}{BOLD}Happy New Year, Luke.{RST}"))
        out.append(pad(f"{DIM}— and the cube hits its Peak right now —{RST}"))
    else:
        days = secs // 86400
        clock = f"{days:02d}:{secs % 86400 // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}"
        for line in big(clock, GOLD):
            out.append(pad(line))
        out.append(pad(f"{FAINT}DAYS      HOURS     MINS      SECS{RST}"))
        out.append("")
        name, note = act_at(target)
        out.append(pad(f"{MOON}at the bells, the cube is in  {BOLD}{name}{RST}"))
        out.append(pad(f"{DIM}{note}{RST}"))
        out.append("")
        out.append(pad(f"{FAINT}{target:%A %d %B %Y · %H:%M}{RST}"))
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Countdown to the Monolith's New Year.")
    p.add_argument("--target", default="2027-01-01T00:00", help="ISO datetime (local). Default midnight into 2027.")
    p.add_argument("--once", action="store_true", help="Print one frame and exit.")
    p.add_argument("--for", dest="run_for", type=float, default=None, help="Run for ~N seconds then exit (failsafe).")
    a = p.parse_args(argv)

    try:
        target = dt.datetime.fromisoformat(a.target)
    except ValueError:
        print(f"bad --target {a.target!r} (use e.g. 2027-01-01T00:00)", file=sys.stderr)
        return 2

    if a.once:
        print(frame(target, dt.datetime.now()))
        return 0

    start = time.monotonic()
    sys.stdout.write(HIDE)
    try:
        while True:
            sys.stdout.write(CLEAR + frame(target, dt.datetime.now()))
            sys.stdout.flush()
            if a.run_for is not None and (time.monotonic() - start) >= a.run_for:
                break
            if target - dt.datetime.now() <= dt.timedelta(seconds=-3):
                break  # lingered a moment on the bloom, then done
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
