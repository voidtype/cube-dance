# `web/` — the cube, in a browser (effect preview)

A pure-additive browser preview of Cube Dance. It runs the **real Python engine
unchanged** — `web/` imports `cube_dance` as-is; nothing in the package was
edited. Drag in an audio file to swap the track, or a `.py` effect to preview it.

```sh
uv run python web/serve.py        # -> http://localhost:8137/web/
```

Open it, click **Start**, and the cube reacts to **Smooth Operator** (the test
track). Drag-orbit, scroll-zoom. Use the panel (bottom-left) to switch effect,
turn the knobs, hit the pads.

## How it works

| layer | tech | notes |
|---|---|---|
| effects engine | **Pyodide** (CPython + numpy, WASM) | the real `cube_dance` engine + all 57 presets, imported from a live zip of the package (`/cube_dance.zip`). ~5 ms/frame. |
| render | **Three.js** (r184) | the 9,744 LEDs as an additive point cloud + UnrealBloom; OrbitControls. |
| audio | **Web Audio** | stereo FFT → bass/mid/treble/8 buckets/beat/kick, in the same shape as the engine's `Features`. |
| controller | HTML | preset picker, the preset's knobs + trigger pads. |
| glue | `web/bridge.py` | the only new Python — imports the engine, owns the colour + feature buffers, exposes `step(t)`. Includes one WASM compat shim (`np.choose` int dtype). |

**Drag in a `.py`** with a `build(engine)` (and optional `KNOBS`/`TRIGGERS`), or
an `Element` subclass named `Effect`, and it previews live — the same contract as
a preset module.

Note: it's a **preview / source for effects**, not an output device — no sACN
here. The effects you make are real `Element`s, so they also run on the desktop
app and the physical rig.

Files: `index.html` · `main.js` · `bridge.py` · `serve.py` (all new; the engine
package is untouched).
