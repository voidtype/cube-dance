"""Command-line entrypoint for the Cube Dance simulator (Phase 0)."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cube-dance",
        description="Interactive 3D LED simulation of the truss cube (Phase 0).",
    )
    p.add_argument(
        "--selftest",
        action="store_true",
        help="Run the headless data-path self-test and exit (no window).",
    )
    p.add_argument(
        "--frames", type=int, default=120, help="Frames to advance during --selftest."
    )
    p.add_argument(
        "--edge-density",
        type=float,
        default=None,
        dest="edge_leds_per_m",
        help="Edge LEDs per metre (default 60).",
    )
    p.add_argument(
        "--corner-density",
        type=float,
        default=None,
        dest="corner_leds_per_m",
        help="Corner LEDs per metre (default 120; must exceed edge density).",
    )
    p.add_argument("--no-floor", action="store_true", help="Hide the clay ground.")
    p.add_argument("--no-speakers", action="store_true", help="Hide the speaker scenery.")
    p.add_argument("--no-bushes", action="store_true", help="Hide the surrounding bushes.")
    p.add_argument("--no-truss", action="store_true", help="Hide the aluminium truss structure.")
    p.add_argument(
        "--audio", type=str, default=None,
        help="Path to an audio file (WAV/FLAC/AIFF/OGG) to play as a VU meter.",
    )
    p.add_argument("--demo", action="store_true", help="Use a synthetic demo beat (no file needed).")
    p.add_argument("--mute", action="store_true", help="Do not play sound; drive the visuals silently.")
    p.add_argument(
        "--visual", choices=["auto", "spectrum", "vu"], default="auto",
        help="Visual: spectrum (cube-aware bass/treble), vu (Phase-1 meter), or auto.",
    )
    p.add_argument("--record", action="store_true", help="Start recording an MP4 at launch (V toggles; stops on quit).")
    p.add_argument("--record-fps", type=int, default=30, help="Recording framerate (default 30).")
    p.add_argument("--record-dir", type=str, default="recordings", help="Output folder for recordings.")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    # Unknown args (e.g. moderngl-window's --window/--vsync) pass through.
    ns, extra = parser.parse_known_args(argv)

    overrides = {
        "edge_leds_per_m": ns.edge_leds_per_m,
        "corner_leds_per_m": ns.corner_leds_per_m,
    }
    overrides = {k: v for k, v in overrides.items() if v is not None}
    if ns.no_floor:
        overrides["show_floor"] = False
    if ns.no_speakers:
        overrides["show_speakers"] = False
    if ns.no_bushes:
        overrides["show_bushes"] = False
    if ns.no_truss:
        overrides["show_truss"] = False

    audio_file = None
    loop = False
    if ns.demo:
        from .audio.demo import make_demo

        audio_file = make_demo()
        loop = True  # keep the demo beat going
    elif ns.audio:
        from .audio import AudioFile

        audio_file = AudioFile.load(ns.audio)

    if ns.selftest:
        from .config import CubeConfig
        from .selftest import run_selftest

        return run_selftest(
            frames=ns.frames, cfg=CubeConfig(**overrides), audio_file=audio_file, visual_choice=ns.visual
        )

    from .app import run

    run(
        config_overrides=overrides, extra_args=extra, audio_file=audio_file, mute=ns.mute, loop=loop,
        visual_choice=ns.visual, record_auto=ns.record, record_fps=ns.record_fps, record_dir=ns.record_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
