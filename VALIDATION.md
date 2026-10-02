# Validated Windows checkpoint

## v0.3.0 — task-specific CPU/GPU selection

- 48/48 tests pass after packaging, no skips. New tests cover encoder/device
  allowlists, unavailable CUDA/runtime paths, live-test-only eligibility, FFmpeg
  device-index parsing, probe timeouts, disabled GPU choices, independent task
  selectors, tool-change invalidation, FP16 decoding, and output preservation on
  failed GPU preflight.
- Source and frozen probes identify RTX 4070 Laptop GPU and Intel UHD Graphics.
  Real CUDA matrix/FFT kernels pass; actual NVENC and QSV encoding probes pass.
  AMF is rejected (no AMD device/runtime on this machine).
- Real **packaged** medium-model CUDA transcription + NVENC caption rendering passed.
  Packaged Intel QSV rendering, subtitle muxing, and CPU medium-model transcription
  + libx264 rendering also passed. The recognized synthetic speech matches the
  baseline text. No model or driver was downloaded or modified.
- No-usable-GPU path verified with the frozen probe: CUDA devices hidden in that
  child environment and no FFmpeg selected; both GPU lists empty. Applying the
  report to the real GUI disables the GPU options with `no compatible GPU found`
  and keeps CPU selected. No system-wide environment changes were made.
- Source GUI background scan completed while its UI heartbeat kept advancing;
  device panel screenshot reviewed. Probe processes use the existing process-tree
  isolation/cancellation mechanism.
- Build uses official PyTorch **2.10.0+cu128**, bundling CUDA 12.8 runtime libraries.
  The lockfile also supports the mutually exclusive CPU-only development extra.
- `dist/v0.3.0/LocalCaption/LocalCaption.exe` is the current Windows release.

Limitations: AMD AMF success and multiple-card systems are implemented but not
hardware-tested here. Intel/AMD encoders use the default driver-selected adapter.
Intel/AMD/MPS inference and macOS encoding backends are not enabled. A small probe
cannot guarantee every model fits VRAM or every video meets an encoder's limits.

## v0.2.1 — drops on the native video surface

- Fixed native-window drag routing: the visible video surface is not the outer
  QVideoWidget used by the original drop test. Both native render-window and
  owning-window drag events are now handled within the preview bounds.
- New regression fails with the fix disabled. Tests cover native drag enter/move/drop,
  playback, disabled controls, output-pane rejection and remote-URL rejection.
- Native event tests pass with the real Windows platform plugin as well as offscreen.
- A real Windows OLE drag from a temporary local-file source onto the video surface
  completed with CopyAction and emitted the expected path. This was a source-build
  native test, not an automated Explorer test against the frozen app.
- Final full suite: 36/36 passing, no skips. Versioned executable rebuilt at
  `dist/v0.2.1/LocalCaption/LocalCaption.exe`; packaged burn/mux smoke tests pass.

## v0.2.0 — synchronized previews

- 32/32 tests pass after packaging, no skips in the final run.
- Native path normalization covers model/settings/browse/drop/manual field values.
- Real Qt Multimedia tests cover two decoded poster frames without autoplay, paired
  playback/pause/stop, forward/back seeking, slider seeking, drift correction,
  single-source audio selection, direct drop onto the video surface, and release of
  output file handles before replacement. GUI re-render with a loaded preview passes.
- Native source GUI comparison visually inspected with both videos showing the same
  moving test-pattern frame. Packaged GUI launched with two local media paths; its
  shared Play button advanced the timeline and changed to Pause, then closed cleanly.
- Packaged FFmpeg burn/mux smoke tests pass; source GUI also drives the new packaged
  worker successfully. Real model inference results below are from v0.1.0; this
  iteration changes GUI/packaging, not the inference engine.
- Distribution now lives in `dist/v0.2.0/LocalCaption/`. Qt Multimedia decoder
  dependencies are included by PyInstaller. External FFmpeg CLI tools remain external.
- UI Automation did not expose Qt descendants in this environment; frozen-window
  checks used a process-specific native mouse message and window-only capture instead.

## v0.1.0 baseline


## Environment

- Windows 11 x64, managed Python 3.12.13, PySide6 6.10.2.
- PyInstaller 6.19.0, OpenAI Whisper 20250625, PyTorch 2.10.0+cpu.
- External FFmpeg/FFprobe 9.0.1 full build already present on the machine.
- Full dependency resolution: uv.lock.

## Passed

- 25 unittest tests, no skips in the final run (about 5 seconds).
- Original backup's six caption-splitting regression tests retained.
- SRT rounding, Unicode, invalid cues, numbered filenames, source/hardlink protection.
- Output preservation on failure; atomic no-clobber publication and explicit replacement.
- Real FFmpeg burn on silent video and selectable mov_text subtitle mux.
- Rendered first-frame pixels differ from source; edited SRT bytes unchanged.
- Paths containing spaces, apostrophes and non-ASCII characters.
- Qt local-file drag/drop events; GUI mode changes; source and frozen worker
  startup/progress/completion/cleanup through QProcess.
- Worker termination stops child heartbeat (Windows Job Object cancellation).
- Native font metrics distinguish narrow/wide glyphs, including Cyrillic measurement.
- Progress adapter restores Whisper state even when inference fails.
- Packaged window opened with expected title and closed normally, exit code 0.
- Native GUI screenshot reviewed (development artifact `.tools/gui-native.png`).
- Final rebuilt packaged worker passed edited-SRT burn, mux and real medium-model
  transcription followed by rendering. Speech was generated locally with Windows
  System.Speech: "Hello world. This is a local subtitle test." The recognized SRT
  contained the expected words and short timed cues.

The existing sandbox-stored medium.pt was read as data, not modified, and checked
against the official Whisper model URL's SHA-256 before inference:
`345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1`.
No model was downloaded; no sandbox Python or auto_subtitle code was executed.

## Packaging notes

The PyInstaller build emits optional-module warnings for tensorboard, Linux libgomp
references and the optional numba TBB backend. The tested CPU inference path does
not require those modules; actual frozen word-timestamp inference passed. These
warnings are not evidence that every optional upstream capability is supported.

The current output is `dist/v0.3.0/LocalCaption/LocalCaption.exe`, its worker exe, shared runtime
folder and documentation. Build artifacts and private development tooling are
intentionally not tracked in Git.

## Not yet validated / out of scope

- macOS/Linux builds, Apple Silicon, signing/notarization, installer/updater.
- Russian speech/automatic-language inference, long-form memory benchmarks,
  AMD/multiple-GPU success cases, and a broad codec/HDR/variable-frame-rate/device
  compatibility matrix.
- The packaged app running *inside* Sandboxie or cross-boundary drag/drop.
- Adversarial-media security audit or strict OS-level network isolation.
- Distribution-license clearance. See SECURITY.md before redistribution.
