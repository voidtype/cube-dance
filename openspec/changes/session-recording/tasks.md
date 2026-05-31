## 1. Dependencies

- [x] 1.1 Add `imageio-ffmpeg` via `uv add` (bundled ffmpeg fallback).

## 2. Recorder module

- [x] 2.1 `recording.py`: `find_ffmpeg()` — `$CUBE_FFMPEG` → `PATH` ffmpeg → `imageio_ffmpeg.get_ffmpeg_exe()`; raise a clear error if none.
- [x] 2.2 `recording.py`: `audio_segment(audio, start_s, dur_s, loop)` — return the `(m, ch)` samples for the window, wrapping if `loop` else zero-padding past the end.
- [x] 2.3 `recording.py`: `SessionRecorder` — `start()` spawns the video ffmpeg (rawvideo rgb24 stdin → H.264/yuv420p/+faststart temp), records start wall-time + audio position, locks WxH (even dims); `due(now)` gates capture to the target fps; `write_frame(rgb_bytes, w, h)` resizes if needed and pipes; `stop()` closes video, writes the audio slice to a temp WAV, muxes to the final timestamped `.mp4`, cleans temps, returns the path.
- [x] 2.4 `recording.py`: guard subprocess errors; `is_recording`, `elapsed` properties.

## 3. Viewer integration

- [x] 3.1 `app.py`: capture the framebuffer (RGB) **after the scene, before the HUD** when `recorder.due(now)`; feed `SessionRecorder`.
- [x] 3.2 `app.py`: key `V` toggles recording; show a `● REC m:ss` line in the HUD while active; print the saved path on stop.
- [x] 3.3 `app.py`: `on_close` finalises an in-progress recording.
- [x] 3.4 `cli.py`: `--record` (auto-start), `--record-fps` (default 30), `--record-dir` (default `recordings/`); pass through to the app.

## 4. Verify & document

- [x] 4.1 `tests/`: `audio_segment` (length, wrap vs pad), `find_ffmpeg` returns an existing path.
- [x] 4.2 Headless: record a few seconds from a hidden window (`--demo --mute`), then `ffprobe` the output to assert an H.264 video + AAC audio stream and ~expected duration. Watchdog + timeout guarded; skip if no ffmpeg.
- [x] 4.3 Update `README.md`: recording key, `--record*` flags, output location, FB compatibility note.
- [x] 4.4 `openspec validate session-recording --strict` passes.
