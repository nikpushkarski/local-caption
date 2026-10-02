# Work checkpoints

## Iteration 7 — CPU/GPU task selection (complete, v0.3.0)
- Separate transcription and burn-video selectors: CUDA inference and hardware
  video encoding are different capabilities. CPU remains the default.
- Scan in an isolated background process, inventory adapters, test CUDA kernels
  and short FFmpeg hardware-encode operations before enabling GPU entries.
- Disable unavailable GPU choices with exact text `no compatible GPU found` and
  provide diagnostic reasons. Rescan on tool changes; allow manual refresh.
- Mux/SRT-only actions must not pretend to benefit from GPU video encoding.
- This machine reports an RTX 4070 Laptop GPU (8 GB) and Intel UHD Graphics.
  Existing package uses CPU-only PyTorch; add a reproducible CUDA build variant
  rather than falsely declaring the RTX incompatible or silently using CPU.
- Implemented background probe UI, disabled GPU placeholders, task-specific mode
  handling, allowlisted encode options and explicit CUDA inference (FP16 decoding).
- Added mutually exclusive `transcribe` (CPU-only) and `cuda` dependency extras.
  Installed official PyTorch 2.10.0+cu128 in the development environment; no drivers
  or models downloaded/changed. CUDA package download was ~2.7 GiB.
- Live probes: RTX CUDA + NVENC and Intel QSV pass; AMD AMF rejected (no AMD device).
  The first 128px probe was below NVENC's minimum frame size; changed to 640x360.
- Real source-worker medium-model CUDA transcription + NVENC render passed; Intel
  QSV rendering and mux also passed.
- Final CUDA-capable build completed under dist/v0.3.0/LocalCaption. All 48 tests
  pass, no skips. Frozen CUDA+NVENC medium inference/render, QSV rendering, CPU
  medium inference/render and subtitle mux all passed. Frozen hardware probe
  matches source; no-usable-GPU disabled-option path verified separately.
- Used FFmpeg's own NVENC device listing instead of assuming nvidia-smi indices
  match encoder ordinals. Device scan UI stayed responsive (heartbeat verified).
- README, SECURITY and VALIDATION describe runtime size, backend limits, automatic
  probing, memory caveats, and mutually exclusive CPU/CUDA build extras.

## Iteration 6 — native preview drop fix (v0.2.1, complete)
- Reproduced the missed path: QVideoWidget embeds a native QVideoWindow whose
  drag events never reach the outer QWidget's overrides. Previous synthetic
  tests targeted the outer widget only, explaining the false confidence.
- Route native-window drag enter/move/drop events within the preview bounds to
  the same validated drop handler. Preserve disabled-state and output-pane guards.
- Added actual render-window regression tests, including video playback. Confirmed
  the new test fails with the fix disabled. All three native-event tests also pass
  with the real Windows Qt platform plugin, not just the offscreen test platform.
- Real Windows OLE drag from a temporary source onto the video surface passed
  (CopyAction and expected file signal). Initial automation attempts released too
  soon before mouse input was processed; after waiting for the button state and
  sending a motion event, the native drag completed. Pointer restored afterward.
- Native Windows can also route OLE through the owning QWidgetWindow; added that
  regression path too. Final suite: 36/36 passing, no skips. Versioned v0.2.1 exe
  built; packaged burn/mux smoke tests pass. No prior running user app closed.

## Iteration 5 — paired video previews (complete, v0.2.0)
- User feedback: native Windows path separators; input drop-preview; adjacent output
  preview; shared playback, stop, forward/back controls.
- Tagged baseline `checkpoint-before-previews` before changes.
- File fields now normalize native separators on browse/drop/settings/manual edit.
- Added Qt Multimedia paired players in Job, with shared play/pause/stop, ±5-second
  skips, seek slider, drift correction, and single-source audio selection.
- Input video surface accepts drops. Existing output is loaded automatically and
  refreshed after processing. Output player is released before atomic replacement.
- Preview decoding occurs on selection (before Start); README/SECURITY updated.
- Tests cover native separators, direct video drops, actual dual decoding, posters,
  shared transport, drift correction, audio selection and Windows file-handle release.
- Final suite: 32/32 tests passing. Versioned Windows build, frozen GUI playback
  check, packaged burn/mux smoke tests and native visual inspection completed.
- An in-place build was blocked by the user's still-running v0.1.0 app after
  PyInstaller began clearing the old distribution. No running user process was
  terminated. Legacy `dist/LocalCaption` may be incomplete; use the fully rebuilt
  `dist/v0.2.0/LocalCaption/LocalCaption.exe` to relaunch. Build script now uses
  versioned output and checks for running copies before modifying that release.
- One pre-build test run hit a transient Windows access-denied error replacing a
  tiny test file. Repeated full runs passed without modifying publication semantics.
- UI Automation could not enumerate Qt controls here; dropped that attempted smoke
  script. Checked the frozen Play control using native messages to the test process.
- Native GUI screenshot evidence is ignored under .tools; no screenshots in Git.


## Contract
Build a local replacement for the user's AutoSubtitleBackups script; eliminate
`auto_subtitle`, add a drag/drop Windows desktop GUI and executable packaging,
and keep the architecture ready for a later macOS build. Leave backups untouched.

## Iterations
1. Audit + repository checkpoint (complete).
2. Local subtitle core and regression tests (complete; 12 passing).
3. Offline processing worker, GUI, and safe output handling (complete; 20 tests passing).
   Real FFmpeg burn/mux integration verified, including silent video, Unicode/apostrophe
   paths, first-frame caption pixels, and unchanged edited SRT. Qt drag/drop events tested.
4. Packaging, cancellation/transcription tests, documentation and final validation (complete).
   24 tests passing, including Qt-driven source and frozen worker lifecycles.
   Windows one-folder exe built; native desktop launch/close verified (exit 0).
   Frozen worker burn, mux, and actual medium-model transcription+burn all passed.
   Official medium SHA256 verified read-only before inference:
   345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1.
   Speech was generated locally using Windows System.Speech. No model downloaded.
   Native screenshot reviewed. Found Windows offscreen Qt font discovery returns
   box glyphs; switched the windowless worker to native desktop font discovery.
   Rebuilt with native font discovery; added a real-font-width regression test.
   Final suite: 25/25 passing, no skips on this machine. Rebuilt frozen worker
   re-passed burn, mux and medium-model transcription+burn smoke tests.
   PowerShell blocked script execution under the default policy; used process-only
   -ExecutionPolicy Bypass for our build script. No persistent policy was changed.
   See VALIDATION.md for evidence and remaining platform/distribution limits.

## Behavioral changes
- Five explicit actions replace the nested console prompts. Mux takes the desired
  existing video as input and writes a separate MP4 (source is never replaced).
- GUI shows elapsed time, activity and confirmed transcription checkpoints instead
  of a history-based estimated ETA. This avoids presenting guesses as progress.
- Windows Job Object ties FFmpeg lifetime to worker lifetime; POSIX uses process groups.
- GUI owns staging directory on the output volume so worker cancellation can be cleaned.
- Atomic no-clobber output publication uses hard links (fails safely if unsupported).

## Audit / decisions
- Backup `sandbox_auto_subtitle.py` imports only `auto_subtitle.utils.write_srt`.
- Also uses Whisper, PyTorch (indirectly), ffmpeg-python, FFmpeg/FFprobe, Windows GDI.
- Preserve CPU / beam 10 / word timestamps / en, ru, auto defaults.
- Preserve 4-word, 24-character, 1.5-second captions and 0.35-second pause splits.
- Replace ffmpeg-python with explicit subprocess argument lists (no shell).
- Use PySide6 for native drag/drop, responsive GUI and cross-platform font metrics.
- Separate GUI from a subprocess worker: cancellation can terminate inference.
- Require a local model file; never download models at runtime.
- Keep FFmpeg and models external; one-folder PyInstaller build with a Windows exe.
- No host Python detected initially. Provisioned uv 0.11.6 and managed Python 3.12.13,
  then project-local .venv. Installed pinned Qt/PyInstaller; no sandbox code executed.
- Caption/layout functions adapted from the user's script; local SRT writer implemented
  from scratch. Windows-only GDI replaced by Qt font metrics.
- Backup archive and third-party auto_subtitle repository will not be executed.

## Resume
Read this file and README.md, inspect `git log --oneline` and `git status`, then run
`.venv/Scripts/python -m unittest discover -s tests -v` (Windows).
Each logical iteration is committed. No automatic reset/revert loop is needed.
