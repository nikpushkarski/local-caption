# Validated Windows checkpoint

> The historical binaries described below (v0.1.0–v0.4.1) were withdrawn from
> GitHub on 2026-10-02. They did not include the updated third-party notices;
> the old v0.4.1 CUDA bundle also included unreviewed NVIDIA DLLs. Keep the
> historical test record separate from current distribution status.

## v0.4.2 — replacement Windows builds (2026-10-02)

- Both CPU and CUDA editions rebuilt from the merged MIT-licensed source. Each
  build passes 64 unit tests (1 Windows temporary-file skip); both include the
  project license, third-party notices and original wheel/CPython license texts.
  Verified 7-Zip archives: CPU ~191 MiB, CUDA ~1832 MiB (one file under GitHub's
  per-asset limit).
- Packaged CPU worker burn and subtitle-track mux smoke tests pass. Packaged CUDA
  worker burn/mux plus `medium.pt` GPU (`cuda:0`) transcription/burn pass on an
  RTX 4070 Laptop GPU. FFmpeg and the model remained external.
- The CUDA bundle contains only the 21 inventoried NVIDIA DLLs; the three
  unreviewed/unneeded extras are absent. The collector rejects unexpected CUDA
  DLLs or a changed CUDA PyTorch wheel. See [CUDA_REDISTRIBUTION.md](CUDA_REDISTRIBUTION.md).

## Release packaging and CPU edition

- Git-tracked source remains under 1 MB. Local `dist/`, `.venv*`, `build/` and
  `.tools/` are ignored build artifacts; CUDA PyTorch accounts for most disk usage.
- The v0.4.1 CPU edition uses PyTorch 2.10.0+cpu: 0.65 GiB extracted, ~219 MiB
  archived. The packaged GUI opened; the packaged worker passed a real local
  `medium.pt` transcription, burn and mux. Hardware video encoding remains possible
  when the user's external FFmpeg supports it; CUDA transcription is disabled.
- The v0.4.1 CUDA edition is optional: 4.47 GiB extracted, ~2.4 GiB archived in
  two parts. These historical editions were withdrawn from GitHub on 2026-10-02.
  Older Windows releases v0.1.0, v0.2.0 and v0.2.1 had also been smoke-tested.
- v0.3.0/v0.4.0 are still running on the developer's machine. Their ignored build
  directories were retained rather than terminating a user process; other inactive
  duplicate artifacts and local release archives were cleaned after upload.

## v0.4.1 — compact two-column layout

- Subtitles / Video and output share one row under the full-width previews.
  Local tools and model / Processing devices share the next row.
- Subtitle controls use a 2×2 grid. Device/action dropdown sizing no longer forces
  the entire window wider when labels are long. Existing behavior is unchanged.
- 64/64 tests pass after packaging, no skips. Structural layout checks plus a native
  Windows font/layout test verify aligned columns without horizontal scrolling at
  1120px and 1000px widths, including selected long GPU names.
- Source and packaged native GUI layouts visually reviewed. Packaged sample
  playback, GUI/worker lifecycle, FFmpeg burn and mux smoke tests pass.
- Current CPU release: `dist/v0.4.1-cpu/LocalCaption/LocalCaption.exe`;
  optional CUDA release can be rebuilt as `dist/v0.4.1/LocalCaption/LocalCaption.exe`.

## v0.4.0 — live sample captions and four style controls

- Final rebuilt app: 62/62 tests pass, no skips. Original caption defaults still
  pass their regression tests; new tests cover settings validation/default markers,
  custom size/width values, multiline wrapping/SRT output, real custom-font ASS
  rendering, immediate sample creation, no fake-output file writes, view switching,
  white foreground pixels, tiny-video handling and output-pane drop isolation.
- Source and packaged native GUI sample playback visually inspected. The output
  example shows exactly `subs example, lorem ipsum`, with white fill/black outline,
  and updates for custom font, size and 1–3 lines. Controls sit between transport
  and Video path. Native input drop handling remains covered by existing tests.
- A real rotation-tagged video verified that the sample follows displayed portrait
  dimensions. The sample reuses input frames, without a second decoder/render job.
- Packaged CUDA medium-model transcription + NVENC rendering passed with Georgia,
  38px, target 12 characters and up to 3 lines. The generated SRT contained actual
  line breaks and original word times. Packaged default CPU burn/mux tests also pass.
- Edited SRT bytes stay unchanged; custom font/multiline behavior is verified in
  the generated ASS render copy. SRT/mov_text viewers control their own font/size.
- Sample rendering is illustrative, not pixel-identical to libass. Explicit font
  size is a source-pixel maximum, fitted down when needed. Target character width
  is approximate; the fixed example is never truncated to satisfy it.
- Current release: `dist/v0.4.0/LocalCaption/LocalCaption.exe`.

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

The CPU output is `dist/v0.4.1-cpu/LocalCaption/LocalCaption.exe`; an optional CUDA
build uses `dist/v0.4.1/LocalCaption/LocalCaption.exe`, its worker exe, shared runtime
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
