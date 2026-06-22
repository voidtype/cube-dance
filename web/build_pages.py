#!/usr/bin/env python3
"""Build the static GitHub Pages site into a directory (default: ``dist/``).

Reproduces, as code, the previously-manual gh-pages deploy: the ``web/`` app at
the root (the homepage -> scroll -> play experience), an identical copy under
``play/`` (the app branches on the ``/play/`` path for direct-in mode), the
``showcase/assets/`` media (the compact ``_web`` video variants), and the engine
``cube_dance.zip`` (the package + the reference mapping JSON, built by
``serve.engine_zip_bytes`` so it matches the live dev server byte-for-byte).

    uv run python web/build_pages.py            # -> dist/
    uv run python web/build_pages.py --out _site

Then publish the directory to the ``gh-pages`` branch (the deploy workflow does
this automatically on push to main; see .github/workflows/deploy-pages.yml).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from serve import REPO_ROOT, engine_zip_bytes  # same dir; one source of truth for the zip

HERE = Path(__file__).resolve().parent
ROOT = Path(REPO_ROOT)
SHOWCASE_ASSETS = ROOT / "showcase" / "assets"

# Files copied verbatim from web/ to the site root (and into play/).
APP_FILES = ("index.html", "main.js", "bridge.py")

# Large media are gitignored (kept out of the repo on purpose), so they may be
# absent in a clean CI checkout. When missing we skip them; the deploy preserves
# whatever is already on gh-pages (the workflow syncs without --delete).
OPTIONAL_MEDIA = ("anchorite.mp3",)

# dest name under assets/  ->  source file in showcase/assets/ (the small _web
# video variants are renamed to drop the suffix, matching the live site).
ASSETS = {
    "moondance.mp3": "moondance.mp3",
    "moondance.mp4": "moondance_web.mp4",
    "reveal.mp4": "reveal_web.mp4",
    "smooth.mp3": "smooth.mp3",
    "og-image.jpg": "og-image.jpg",
    "storyboard.jpg": "storyboard.jpg",
}

ROBOTS_TXT = "User-agent: *\nDisallow: /\n"  # the preview stays unlisted


def build(out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    play_dir = out_dir / "play"
    (out_dir / "assets").mkdir(parents=True)
    play_dir.mkdir(parents=True)

    # Engine zip (cube_dance package + reference mapping) — root and play/.
    zip_bytes = engine_zip_bytes()
    (out_dir / "cube_dance.zip").write_bytes(zip_bytes)
    (play_dir / "cube_dance.zip").write_bytes(zip_bytes)

    # The required app files at the root and duplicated into play/.
    for name in APP_FILES:
        src = HERE / name
        if not src.is_file():
            raise SystemExit(f"missing app file: {src}")
        shutil.copy2(src, out_dir / name)
        shutil.copy2(src, play_dir / name)

    # Optional gitignored media (root + play/); preserved on gh-pages if absent.
    for name in OPTIONAL_MEDIA:
        src = HERE / name
        if src.is_file():
            shutil.copy2(src, out_dir / name)
            shutil.copy2(src, play_dir / name)
        else:
            print(f"  (skip, not in checkout) {name}")

    # Showcase media (mp4/mp3 are gitignored; jpgs are tracked). Skip if missing.
    for dest, src_name in ASSETS.items():
        src = SHOWCASE_ASSETS / src_name
        if src.is_file():
            shutil.copy2(src, out_dir / "assets" / dest)
        else:
            print(f"  (skip, not in checkout) assets/{dest}")

    # Static helpers.
    (out_dir / ".nojekyll").write_text("")  # serve files/dirs starting with _
    (out_dir / "robots.txt").write_text(ROBOTS_TXT)

    return out_dir


def _report(out_dir: Path) -> None:
    total = 0
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            total += size
            print(f"  {size:>10,}  {p.relative_to(out_dir)}")
    print(f"\n  {len(list(out_dir.rglob('*')))} entries, {total / 1e6:.1f} MB -> {out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "dist"), help="output directory (default: dist/)")
    args = ap.parse_args()
    out = build(Path(args.out).resolve())
    _report(out)
    return 0


if __name__ == "__main__":
    # `from serve import ...` resolves via the script dir (auto-added to sys.path);
    # no chdir, so a relative --out stays relative to the caller's CWD.
    raise SystemExit(main())
