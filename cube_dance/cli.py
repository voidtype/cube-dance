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
    p.add_argument("--live", action="store_true", help="Drive the visuals from a live audio input (line/mic).")
    p.add_argument("--input-device", default=None, help="Live input device (name substring or index).")
    p.add_argument("--input-gain", type=float, default=1.0, help="Live input gain multiplier (default 1.0).")
    p.add_argument("--list-audio-inputs", action="store_true", help="List available audio input devices and exit.")
    p.add_argument("--input-test", action="store_true", help="Open the live input and print the captured level for a few seconds, then exit.")
    p.add_argument("--mute", action="store_true", help="Do not play sound; drive the visuals silently.")
    p.add_argument(
        "--visual", choices=["auto", "spectrum", "vu"], default="auto",
        help="Visual: spectrum (preset-driven element engine), vu (Phase-1 meter), or auto.",
    )
    p.add_argument("--preset", default="atlas", help="Visual preset for the element engine (e.g. atlas, deep, punchy).")
    p.add_argument(
        "--set", dest="show", default=None, metavar="NAME",
        help="Run an autonomous SHOW that performs a whole night on its own (e.g. 'dustlight', the "
             "DUSTLIGHT rave arc: dusk Arrival → Peak → Deep Trip → Sunrise). Open the F1 panel to take over.",
    )
    p.add_argument(
        "--set-minutes", dest="show_minutes", type=float, default=2.5,
        help="Compress the show's whole night into this many minutes, then loop (default 2.5).",
    )
    p.add_argument("--record", action="store_true", help="Start recording an MP4 at launch (V toggles; stops on quit).")
    p.add_argument("--record-fps", type=int, default=30, help="Recording framerate (default 30).")
    p.add_argument("--record-dir", type=str, default="recordings", help="Output folder for recordings.")
    return p


def _input_test(device, gain: float) -> int:
    """Open the live input, print the captured level for a few seconds, then exit."""
    import os
    import sys
    import threading
    import time

    import numpy as np

    from .audio import LiveAudioInput

    live = LiveAudioInput(device=device, gain=gain)
    print(f"Live input {device!r} @ {live.sr} Hz — capturing ~4s, play some audio…")
    threading.Timer(12.0, lambda: (print("\n[timeout] exiting"), sys.stdout.flush(), os._exit(0))).start()
    live.start()
    time.sleep(0.6)  # let the device open
    if not live.active and live.error:
        print(f"  could not open input: {live.error}")
    peak = 0.0
    for _ in range(40):
        time.sleep(0.1)
        w = live.window_at(0.0, 4096)
        rms = float(np.sqrt(np.mean(w ** 2)))
        peak = max(peak, float(np.max(np.abs(w))) if w.size else 0.0)
        bar = "#" * int(min(1.0, rms * 4.0) * 40)
        print(f"  |{bar:<40}| rms={rms:.3f} peak={peak:.3f}   ", end="\r", flush=True)
    print()
    print(f"  active={live.active} peak={peak:.3f}")
    if peak < 1e-4:
        print("  -> NO SIGNAL on this device. Set the macOS Sound *Output* to it (so apps")
        print("     play into it) and double-check --input-device.")
    live.close()
    return 0


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

    if ns.list_audio_inputs:
        from .audio import list_input_devices

        print("Audio input devices:")
        for line in list_input_devices():
            print("  " + line)
        return 0

    dev = ns.input_device
    if dev is not None and dev.lstrip("-").isdigit():
        dev = int(dev)

    if ns.input_test:
        return _input_test(dev, ns.input_gain)

    audio_file = None
    loop = False
    if ns.live:
        from .audio import LiveAudioInput

        audio_file = LiveAudioInput(device=dev, gain=ns.input_gain)
    elif ns.demo:
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
        visual_choice=ns.visual, preset=ns.preset, show=ns.show, show_minutes=ns.show_minutes,
        record_auto=ns.record, record_fps=ns.record_fps, record_dir=ns.record_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
