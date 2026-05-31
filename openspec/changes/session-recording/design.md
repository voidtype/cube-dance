## Context

The viewer already renders to a framebuffer we can read (proven by the offscreen captures),
and `AudioSource` holds the decoded samples + current position. So we can record a live
session without any OS screen-capture: grab our own frames + mux the exact audio.

## Goals / Non-Goals

**Goals:** one-key live recording → a clean, FB-compatible MP4 with synced sound; robust
ffmpeg handling; finalise even if the window closes mid-record.

**Non-Goals:** offline/deterministic export, scripted camera paths, OS screen capture,
GPU-accelerated encoders. (Possible later.)

## Decisions

### D1 — Grab our own frames, two-stage mux
Each render, after drawing the scene **but before the HUD**, if a frame is "due" (see D2)
read `self.wnd.fbo` as RGB and write the raw bytes to an ffmpeg subprocess encoding H.264
(`yuv420p`, `-preset veryfast`, `+faststart`) to a temp video. On stop, write the audio
slice to a temp WAV and run a second ffmpeg to mux (`-c:v copy -c:a aac -shortest`) into the
final MP4. Reading before the HUD keeps the overlay out of the file.

### D2 — Fixed share framerate, decoupled from render rate
Record at a target fps (default 30). Capture a frame only when `wall_now - last_capture >=
1/fps`, and tell ffmpeg the input `-framerate`. This yields correct-speed video regardless
of the live render rate and halves readback cost vs every frame. Frames are resized to the
locked recording size if the window is resized mid-record.

### D3 — Audio alignment
At start, record `audio.position` and wall-clock. The recorded video is real-time at correct
speed and the audio plays in real-time, so on stop we take `samples[start : start + elapsed]`
(wrapping for a looped source, zero-padding otherwise) and mux it. This keeps A/V within a
frame. Muxed even when `--mute`; omitted when there is no audio source.

### D4 — ffmpeg discovery + robustness
`find_ffmpeg()` returns the first of: `$CUBE_FFMPEG`, `ffmpeg` on `PATH`, then
`imageio_ffmpeg.get_ffmpeg_exe()`. The recorder guards subprocess start; `on_close`
finalises an in-progress recording so the file is always playable.

## Risks / Trade-offs

- **Readback stalls** at high res → Mitigation: 30 fps sampling; veryfast preset; accept a
  modest live-fps dip while recording.
- **Cannot verify on a real display here** → Mitigation: produce a clip from a hidden window
  headlessly and validate it with `ffprobe` (streams, duration); guard all runs with a
  watchdog + timeout.
- **A/V drift** if playback isn't real-time → only an issue in the virtual-clock fallback;
  acceptable for a share clip.

## Open Questions

- Default 30 fps / native resolution chosen here; a `--record-size`/square crop for FB
  stories could be added if wanted.
