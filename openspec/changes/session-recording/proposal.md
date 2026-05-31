## Why

We want to share the cube visuals on social media (Facebook). That needs a one-button way
to capture a **live session** — the cube reacting to the music, with the user's own camera
moves — into a clean, broadly-compatible video file with sound.

## What Changes

- Add a **session recorder**: a key toggles recording while the viewer runs. It captures
  the app's **own rendered frames** (the clean scene — the HUD/REC overlay is excluded
  from the file) at a fixed "share" framerate, pipes them to **ffmpeg** (H.264 / yuv420p),
  and on stop **muxes the audio that played** (AAC) into a final **MP4** with `+faststart`
  — the H.264/AAC MP4 combo plays on Facebook and basically everywhere.
- On screen the user still sees a **REC indicator + elapsed time**; the recorded file does
  not include it.
- Resolve **ffmpeg** from `PATH`, falling back to a **bundled** binary (`imageio-ffmpeg`)
  so it works on any machine.
- CLI: **`--record`** to auto-start at launch (and stop on quit), **`--record-fps`**,
  **`--record-dir`**; in-session key **`V`** toggles. Output is a timestamped `.mp4`.
- Works with `--demo`/`--audio`. The audio is muxed even when `--mute` (so the clip has
  sound); with no audio source the clip is video-only.

Explicitly **out of scope**: an offline deterministic export / scripted auto-orbit camera
(could be added later), and OS-level screen capture (we grab our own framebuffer instead).

## Capabilities

### New Capabilities
- `recording`: Capturing a live session's rendered frames plus the played audio into a
  shareable MP4 (H.264 + AAC), toggled in-session, with an on-screen indicator and robust
  ffmpeg handling.

### Modified Capabilities
<!-- None — the viewer gains a key + indicator but its rendering contract is unchanged. -->

## Impact

- New dependency: `imageio-ffmpeg` (bundled ffmpeg fallback; prefers system ffmpeg).
- New module `cube_dance/recording.py`; viewer gains a record key, a REC HUD indicator,
  and finalisation on close; new CLI flags.
- Reads the window framebuffer and the `AudioSource` samples/position; no change to the
  cube model or the color-buffer contract.
