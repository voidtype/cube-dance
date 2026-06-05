# `showcase/` — *the cube into 2027*

A scroll-driven pitch page made for **Luke**: the system that sends his cube into
2027, scored by **Moondance** (the journey) and revealed with **Smooth Operator**
(the hit), with a live countdown to midnight on New Year's Eve.

The narrative ties the whole project together: **DUSTLIGHT** — the dusk-to-sunrise
show the cube already performs (`cube_dance/show.py`) — given a real date,
**NYE 2026 → 2027**, where the *Peak* act lands exactly at midnight.

## What's here

| file | what |
|------|------|
| `index.html` | the page (bundle form — loads `assets/`) |
| `cube-into-2027.html` | **the file to send Luke** — fully self-contained (assets inlined), opens with a double-click. *(generated; git-ignored)* |
| `render_clip.py` | renders the cube reacting to a song, offscreen, to mp4 |
| `build_standalone.py` | inlines `index.html` + assets → the single send-able file |
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

# 3) build the one file to send
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

## Send it

`cube-into-2027.html` is ~27 MB and self-contained — AirDrop it, or drop it in a
chat. It opens offline; best with the sound up. Tweak the event date in the page
via the `EVENT_DATE` constant (currently midnight into 2027).

A companion terminal countdown lives at [`../tools/countdown.py`](../tools/countdown.py):

```sh
uv run python tools/countdown.py        # live, Ctrl-C to quit
uv run python tools/countdown.py --once  # one frame
```
