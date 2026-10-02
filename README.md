# Local Caption

Offline Windows desktop captions, replacing the user's sandbox transcription script
without **auto_subtitle** or **ffmpeg-python**. Models, media and subtitles stay local.

## Run the Windows app

Double-click **`dist\v0.4.1\LocalCaption\LocalCaption.exe`**.
Keep the **entire `LocalCaption` folder** together: the worker exe and `_internal`
folder are required. No Python installation is needed to run this build.
This is a portable, unsigned **one-folder build**, not a single-file installer.
Whisper/PyTorch make the folder relatively large.

1. Drop a video onto the window (or use Browse).
2. Choose an action and output filename.
3. Under Local tools, choose trusted `ffmpeg.exe` and `ffprobe.exe` from the same
   FFmpeg installation. The build needs libass and libx264 support. Existing PATH
   tools are suggested, not copied or downloaded.
4. For transcription, choose a **local Whisper `.pt` model**. The original
   `medium.pt` works. Choose English, Russian or automatic detection.
5. In **Processing devices**, keep CPU or select a tested GPU for each task.
6. Click Start. Cancel stops the worker and its FFmpeg descendants.

Tool/model selections persist in Windows user settings. Nothing is written to the
backup. To remain sandboxed, launch the app through Sandboxie's **Run Sandboxed**
command and choose paths visible inside that sandbox. Drag/drop across integrity
levels or a sandbox boundary may be blocked by Windows; Browse remains available.
Do not run the app elevated merely to enable drag/drop.

### Side-by-side video comparison

The **Job** section contains input and output video previews. Drop a video directly
onto the input preview or use the Video field. As soon as it decodes, the output
pane shows the same video with **"subs example, lorem ipsum"** overlaid. This is a
live **Sample captions** view, not a generated output file. It needs no model or
FFmpeg render and follows the input exactly during playback/seek.

The output-pane dropdown switches between **Sample captions** and **Rendered video**
(the latter is disabled until the Output path exists). A completed video job switches
to the real output automatically; changing subtitle settings returns to the sample.
SRT-only jobs keep the illustrative sample but do not create an output video.
Both views show a frame without autoplay.

Use the single **Play/Pause**, **Stop**, **−5 s / +5 s**, and seek slider to control
both videos. Select Input audio, Output audio, or Muted to avoid doubled sound.
The input timeline is the reference; periodic drift correction keeps the output
close. This is synchronized comparison, **not guaranteed frame-accurate editing**.
Durations can differ; a shorter output holds at its end. Preview controls are
unavailable during processing, and the output decoder releases its file so the
worker can safely replace it. Existing embedded subtitles are enabled when supported
by the Qt backend; external edited SRTs appear only after rendering/muxing.

Preview playback uses Qt Multimedia's bundled decoder (separate from your external
FFmpeg tools); a preview codec error does not prevent trying a processing job.
The CPU/GPU processing selectors do not control preview hardware acceleration.
File fields display native Windows backslashes, including saved model paths.
The window scrolls on smaller screens. Optional launch arguments preselect files
without starting a job: `LocalCaption.exe --input "C:\Media\in.mp4" --output "C:\Media\out.mp4"`.

### Subtitle controls

Below the playback controls, **Subtitles** sits in the left column and **Video
and output** fields sit in the right column. The next row pairs **Local tools and
model** with **Processing devices**. Subtitle controls use a compact 2×2 grid:


| Setting | Default | Behavior |
|---|---|---|
| Font | **Arial (default)** | Installed font family; bold/white/black-outline styling stays fixed |
| Font size | **Auto — video-scaled (default)** | Original `min(height × 28/288, width × 0.075)` sizing; select or type 1–512 source-video pixels |
| Target chars / line | **24 (default)** | Select or type 6–120 characters as an approximate line-width target |
| Maximum lines | **1 (default)** | Allow up to 1, 2 or 3 lines; does not force that many lines |

The sample updates immediately without changing the source. Font size is relative
to the video, not the preview widget. Text is fitted down if necessary to stay
inside the frame. Bottom placement and margins retain the original defaults.
Qt paints the illustrative sample using the same font/layout calculations as the
real burn; libass rasterization/line spacing can differ slightly.

The fixed example is never shortened or truncated. With one line allowed, changing
the character target affects real cue grouping but cannot shorten that fixed
example. With multiple lines, the example wraps. Long words remain whole. Generated
cues scale the original four-word budget with target width/line count, retaining
original punctuation, pause and 1.5-second timing limits.

Font/size apply to **burned** captions only. Generated SRTs preserve the requested
line breaks, but their player may reflow them and chooses its own font/size. An
existing edited SRT is never rewritten; burn settings affect only its render copy.
"Add existing SRT as track" keeps that file's contents unchanged, so the style
controls are illustrative only for that action.

### CPU / GPU processing

The app scans devices in a background process at startup and when the selected
FFmpeg changes. **Rescan GPUs** refreshes results after driver/hardware changes.
CPU remains the default, and transcription/encoding have separate dropdowns:

- **Transcription:** CPU or a specific NVIDIA CUDA GPU. The probe executes FP16
  matrix and FFT kernels using this app's PyTorch runtime; a card name alone is not
  proof of compatibility. CUDA decoding uses FP16; CPU decoding stays FP32.
- **Video encoding:** CPU/libx264, NVIDIA NVENC, Intel Quick Sync (QSV), or AMD AMF.
  Each GPU backend must successfully encode three synthetic frames using the
  selected FFmpeg and production encoder settings before it is enabled.
- If a task has no usable GPU, the **GPU — no compatible GPU found** option is
  disabled. **Device details / diagnostics** explains why, including missing
  drivers, CPU-only PyTorch builds, unsupported encoders or failed kernel tests.
- NVIDIA encoder choices use FFmpeg's own device indices, independently of CUDA
  inference indices. Intel/AMD encoders currently use the driver-selected adapter;
  individual adapter selection within those vendors is not implemented.
- GPU encoding accelerates compression, **not** the CPU subtitle layout/libass
  filtering. Selectable subtitle tracks stream-copy video, so their encoding
  selector is disabled. Existing-SRT actions disable the transcription selector.
- Availability is checked again at execution. Failures do not silently switch to
  CPU. An out-of-memory error suggests CPU, a smaller model or freeing GPU memory.
  Scan-time free VRAM is shown in details; successful small probes do not guarantee
  that a particular Whisper model, long recording or video dimensions will fit.
- Intel/AMD GPU transcription, Apple MPS, and macOS VideoToolbox are not enabled in
  this version. Hardware support here means support by these tested app backends.

The current build includes CUDA-capable PyTorch **and selectable CPU processing**, so its folder
is several GB. No CUDA toolkit install is needed to run it, but a compatible NVIDIA
driver is required for CUDA. The current machine's RTX 4070 Laptop GPU passed CUDA
and NVENC tests; its Intel UHD Graphics passed QSV. GPU quality settings are not
numerically equivalent to x264 CRF 18, so output size/quality can differ.

### Actions

| Action | Result |
|---|---|
| Transcribe + burn | New SRT, plus MP4 with captions permanently in the picture |
| Transcribe to SRT only | New SRT; no video encoding |
| Burn existing / edited SRT | Render MP4 without loading Whisper |
| Transcribe + selectable track | New SRT, stream-copied video with a subtitle track |
| Add existing SRT as track | Stream-copied video with a selectable subtitle track |

For the old script's "merge with existing output" action, select that existing
video as **input**, choose a different output name, and use a selectable-track
action. Burned-in captions cannot be removed; use the original video for new burns.
Selectable tracks may be hidden until enabled in your video player.

### Preserved behavior and deliberate changes

- CPU Whisper by default, optional CUDA; beam size 10, word timestamps, English default.
- Default short cues: at most 4 words / 24 characters / 1.5 seconds, split on
  punctuation and pauses over 0.35 seconds. Width/line-count settings adjust the
  word/character budget. A single long word remains intact.
- White bold captions (Arial by default), black outlines, per-cue font fitting,
  rotation-aware sizing. Qt replaces Windows-only GDI font measurement.
- Very short cues are extended only in the render copy; edited SRTs stay untouched.
- Silent videos can be captioned from an existing SRT; transcription requires audio.
- Existing SRTs are never overwritten; numbered names are reserved exclusively.
- Inputs are never overwritten. Existing MP4 output replacement requires explicit
  permission plus confirmation. Rendering is staged before atomic publication.
- Without overwrite permission, publication uses a same-volume hard link to avoid
  race-condition overwrites. Use a local NTFS volume; unsupported filesystems fail
  safely instead of silently falling back to truncation.
- Confirmed transcription progress advances per audio chunk. Loading, decoding
  before the first checkpoint, and rendering show activity plus elapsed time.
  There is **no guessed ETA**, decoder-pass counter or persistent timing cache.
- Burn output is H.264/AAC MP4. Mux copies video/audio; incompatible MP4 codecs can
  fail safely. Burn uses the first video and all audio tracks; mux also retains
  text subtitles. Attachments, chapters and all possible HDR/color metadata are
  not guaranteed to survive. There is no batch queue in this initial version.

## Developer setup

Python 3.12 is recommended. With [uv](https://docs.astral.sh/uv/) installed:

```powershell
uv sync --locked --extra transcribe --extra build
.venv\Scripts\python.exe -m local_caption
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`uv.lock` records transitive dependencies. The `transcribe` extra selects CPU-only
PyTorch on Windows/Linux. For the CUDA-capable Windows build (CPU also supported),
use the mutually exclusive `cuda` extra **instead**:

```powershell
uv sync --locked --extra cuda --extra build
```

This selects official PyTorch CUDA 12.8 wheels and downloads several GB during
setup. Do not combine `--extra transcribe` and `--extra cuda`. Runtime downloads
are not used. Setup/build dependency downloads **do**
require internet. For rendering-only development, omit `--extra transcribe`.
The full packaging spec requires the transcription dependencies.

The initial development environment also has a repository-local uv at
`.tools\uv\uv.exe`; this ignored tooling is not part of the source distribution.

### Build Windows

```powershell
powershell -NoProfile -File scripts\build-windows.ps1
```

If PowerShell blocks this locally reviewed script, use a **process-only** override:
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1`.
This does not change the machine/user execution policy.

Builds go into `dist\v<VERSION>\LocalCaption` so a running older version need not
be replaced. Close this version's app/worker before rebuilding it; the script checks
for running copies before modifying its build output.

Build on Windows x64. Launch the GUI exe, not `LocalCaptionWorker.exe`. The separate
console worker provides reliable JSON progress pipes in a windowed PyInstaller
build. FFmpeg/FFprobe **command-line executables** and model files are external,
intentionally not redistributed. Qt's own native decoder libraries are bundled
for previews and have separate license/security implications.
Before sharing the app publicly, review third-party licenses and signing needs.

### Tests

The standard-library unittest suite covers caption splitting, SRT formatting,
Unicode, no-clobber publication, source preservation, actual Qt drag/drop, worker
cancellation, and FFmpeg rendering/muxing. Media tests skip if FFmpeg/FFprobe are
not on PATH. No test downloads models.

Run packaged media smoke tests:

```powershell
.venv\Scripts\python.exe scripts\smoke-test.py
# Optional full inference test using your own model and spoken WAV:
.venv\Scripts\python.exe scripts\smoke-test.py --model C:\Models\medium.pt --speech C:\Media\speech.wav
```

On this machine, the full packaged worker test passed with the existing official
`medium.pt` and a Windows-generated speech sample: "Hello world. This is a local
subtitle test." English/Russian/auto options are implemented; only English was
exercised with a real model during this iteration.

## Architecture / macOS foundation

- `srt.py`: original local SRT writer, no third-party imports.
- `captions.py`: caption splitting/layout adapted from the user's backup.
- `engine.py`: validated jobs, direct FFmpeg subprocesses, output publication.
- `hardware.py`, `hardware_ui.py`: live capability probes and separate CPU/GPU task selectors.
- `transcription.py`: isolated Whisper progress adapter.
- `worker.py`, `process_tree.py`: one-job subprocess and process-tree lifetime.
- `app.py`: PySide6 native desktop GUI with native-path fields and local-file drag/drop.
- `preview.py`: paired Qt Multimedia players, shared transport and drift correction.
- `subtitle_style.py`, `style_ui.py`: validated style settings and the four controls.
- `sample_preview.py`: live input-frame sample canvas, without writing output files.
- `packaging/`: PyInstaller entry point and Windows one-folder spec.

Core paths use pathlib, process arguments never use a shell, font metrics use Qt,
folder opening uses QDesktopServices, and POSIX cancellation uses process groups.
No Sandboxie paths, Windows drive letters or GDI calls are embedded in processing.

**macOS packaging is intentionally not implemented or validated yet.** Next work:
create a `.app` bundle and embedded worker layout; update frozen-worker path
resolution; build natively per target architecture; test Arial/font fallback and
FFmpeg/libass; validate model memory use; sign/notarize the app and dependencies;
exercise Gatekeeper, file dialogs, drag/drop, cancellation and Apple Silicon.
PyInstaller is not a cross-compiler; the Windows build is not a macOS artifact.

## Recovery / checkpoints

See `PROGRESS.md` and `git log --oneline`. Logical milestones are committed and
annotated tags identify tested checkpoints. Build artifacts, environments, media
and models are ignored by Git and regenerated rather than committed.

If the app/machine crashes, inspect hidden `.local-caption-*` directories beside
its output; delete only a known abandoned job directory after its worker exits.
A successfully generated SRT is retained even if later video rendering fails or
is cancelled. Tool errors appear in the GUI log; copy them before closing.
