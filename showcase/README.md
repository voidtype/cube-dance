# `showcase/` — *the cube, for New Year's at Stumpy*

A scroll-driven page about the cube + the Cube Dance software, ready
for the real **New Year's Eve doof at the Stumpy site in the Watagans**. Scored by
**Moondance** then revealed with **Smooth Operator**, with a live countdown to
midnight on NYE (2026 → 2027).

It leans on the software's real whole-night auto-set (`cube_dance/show.py`, a
dusk-to-sunrise 7-act sequence) and the real output path Luke confirmed —
**sACN E1.31 → his Advatek PixLite 16**. The song choices and the page's framing
are a showcase; the cube footage and the tech are real. (Earlier drafts wrapped
this in an invented "DUSTLIGHT / the Monolith" concept — that was fiction and has
been removed; `show.py` still uses `dustlight` as an internal set name.)

## What's here

| file | what |
|------|------|
| `index.html` | the page (bundle form — loads `assets/`) |
| `cube-into-2027.html` | **the single self-contained file** — assets inlined, opens with a double-click. *(generated; git-ignored)* |
| `render_clip.py` | renders the cube reacting to a song, offscreen, to mp4 |
| `build_standalone.py` | inlines `index.html` + assets → the single self-contained file |
| `assets/` | the rendered clips, web audio, storyboard *(mp4/mp3 git-ignored — regenerate)* |

## The cube footage is real

Both clips are the **genuine LED output** of the real engine reacting to the real
tracks — no colour added in post. The moonlit blue and the gold come from the
LEDs themselves: the palette is locked honestly with the colour + evolve knobs
(`speed≈0` so the hue doesn't drift), not a filter. The only post is a mild
denoise (so the discrete pixels read as smooth tape glow) and H.264 encoding.

## Regenerate everything

Needs the two source tracks on disk (paths in `render_clip.py`) and the project's
`uv` env.

```sh
# 1) render the two cube clips (offscreen, ~1–2 min each)
uv run python showcase/render_clip.py clip moondance --start 88 --dur 52 --w 960 --h 540 --crf 27 --out showcase/assets/moondance.mp4
uv run python showcase/render_clip.py clip reveal    --start 168 --dur 34 --w 960 --h 540 --crf 27 --out showcase/assets/reveal.mp4

# 2) compact variants for the single-file embed + web audio
cd showcase/assets
ffmpeg -y -i moondance.mp4 -r 24 -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p -movflags +faststart moondance_web.mp4
ffmpeg -y -i reveal.mp4 -vf scale=854:-2 -r 24 -c:v libx264 -crf 31 -preset slow -pix_fmt yuv420p -movflags +faststart reveal_web.mp4
ffmpeg -y -i "<Moondance.aiff>" -c:a libmp3lame -b:a 128k moondance.mp3
ffmpeg -y -i "<SmoothOperator.aiff>" -c:a libmp3lame -b:a 128k smooth.mp3
cd ../..

# 3) build the single self-contained file
uv run python showcase/build_standalone.py     # -> showcase/cube-into-2027.html
```

Dial in a look before a full render with the probe mode:

```sh
uv run python showcase/render_clip.py probe moondance --at 96 --out /tmp/m.png
```

## Preview locally

```sh
python3 -m http.server 8131 --directory showcase   # then open http://localhost:8131/
```

## Share it

`cube-into-2027.html` is ~27 MB and self-contained — AirDrop it, or drop it in a
chat. It opens offline; best with the sound up. Tweak the event date in the page
via the `EVENT_DATE` constant (currently midnight into 2027).

A companion terminal countdown lives at [`../tools/countdown.py`](../tools/countdown.py):

```sh
uv run python tools/countdown.py        # live, Ctrl-C to quit
uv run python tools/countdown.py --once  # one frame
```
