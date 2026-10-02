# Local Caption

Offline Windows desktop captions, replacing the user's sandbox transcription script
without **auto_subtitle** or **ffmpeg-python**. Models, media and subtitles stay local.

## Run the Windows app

Double-click **`dist\v0.2.1\LocalCaption\LocalCaption.exe`**.
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
5. Click Start. Cancel stops the worker and its FFmpeg descendants.

Tool/model selections persist in Windows user settings. Nothing is written to the
backup. To remain sandboxed, launch the app through Sandboxie's **Run Sandboxed**
command and choose paths visible inside that sandbox. Drag/drop across integrity
levels or a sandbox boundary may be blocked by Windows; Browse remains available.
Do not run the app elevated merely to enable drag/drop.

### Side-by-side video comparison

The **Job** section contains input and output video previews. Drop a video directly
onto the input preview or use the Video field. The output pane follows the Output
path and reloads the finished MP4 automatically. SRT-only jobs have no output video.
Both previews show a poster frame without autoplay.

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
File fields display native Windows backslashes, including saved model paths.
The window scrolls on smaller screens. Optional launch arguments preselect files
without starting a job: `LocalCaption.exe --input "C:\Media\in.mp4" --output "C:\Media\out.mp4"`.

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

- CPU Whisper, beam size 10, word timestamps, English default.
- Short cues: at most 4 words / 24 characters / 1.5 seconds, split on punctuation
  and pauses over 0.35 seconds. A single long word remains intact.
- White bold Arial-style captions, black outlines, per-cue font fitting, video
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

`uv.lock` records transitive dependencies; uv selects CPU-only PyTorch on Windows
and Linux. Runtime downloads are not used. Setup/build dependency downloads **do**
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
- `transcription.py`: isolated Whisper progress adapter.
- `worker.py`, `process_tree.py`: one-job subprocess and process-tree lifetime.
- `app.py`: PySide6 native desktop GUI with native-path fields and local-file drag/drop.
- `preview.py`: paired Qt Multimedia players, shared transport and drift correction.
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
