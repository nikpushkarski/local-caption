# Local Caption

**Windows app available. macOS support is work in progress.**

Make short, offline subtitles for videos. No `auto_subtitle`, cloud API, telemetry or automatic model downloads. The app has side-by-side video previews and can burn captions into an MP4, save an SRT, or add a selectable subtitle track.

## Get started on Windows

1. Download the **latest Windows release** from [GitHub Releases](https://github.com/nikpushkarski/local-caption/releases). Extract **all** archive parts, if the release has more than one, following its release notes. Keep the extracted `LocalCaption` folder intact; run `LocalCaption.exe` inside it. This is a portable, unsigned app—not an installer.
2. Select or drop a video onto the input preview.
3. Choose trusted local `ffmpeg.exe` and `ffprobe.exe` (from an FFmpeg build with libass and libx264). For transcription, also choose a local Whisper `.pt` model. **These files are not bundled.**
4. Choose an action and output name, adjust subtitles if you like, then press **Start**. CPU is the default. Compatible GPUs appear as optional choices for transcription and video encoding.

The output pane shows an immediate *sample*, not a rendered file. Use its dropdown after processing to compare with the real output. One set of playback controls operates both previews; synchronization is approximate.

| Action | What you get |
|---|---|
| Transcribe + burn | A new SRT and an MP4 with permanent on-screen captions |
| Transcribe to SRT only | A new SRT; no rendered video |
| Burn existing SRT | An MP4 using your edited SRT; no transcription |
| Transcribe + selectable track | A new SRT and an MP4 with a switchable subtitle track |
| Add existing SRT as track | An MP4 with a switchable subtitle track |

**Subtitles:** Choose an installed font (Arial by default), auto or manual font size, target characters per line (24 by default), and up to 1, 2 or 3 lines (1 by default). The sample updates immediately. Font and size affect *burned* captions; the video player controls the appearance of selectable tracks and standalone SRTs.

**GPU:** The app tests devices before offering them. CUDA can speed up transcription; NVENC, Quick Sync or AMF can speed up video encoding. Caption drawing still uses the CPU. If nothing passes the probe, the GPU choice is disabled. The Windows build includes CUDA-capable PyTorch and can also run on CPU; it does **not** require an NVIDIA GPU.

The app never overwrites your input or an existing SRT. Replacing an output video requires confirmation. It can run inside Sandboxie if you prefer; drag-and-drop across a sandbox boundary may be blocked, so use Browse there. Selecting a video previews it immediately, so continue sandboxing untrusted media. See [SECURITY.md](SECURITY.md) for the trust boundaries.

## Build from source

Python 3.12 and [uv](https://docs.astral.sh/uv/) are recommended. On Windows, choose **one** runtime extra:

```powershell
uv sync --locked --extra cuda --extra build       # CUDA-capable + CPU
# OR: uv sync --locked --extra transcribe --extra build  # smaller, CPU-only
.venv\Scripts\python.exe -m local_caption
.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -File scripts\build-windows.ps1
```

If PowerShell blocks the build script, use `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-windows.ps1` (process-only override). Builds go in `dist\v<VERSION>\LocalCaption`. Build dependencies require internet; running the app does not. FFmpeg and models remain external. Before redistributing binaries, review bundled dependency licenses; see [SECURITY.md](SECURITY.md).

macOS packaging is not implemented or tested yet. PyInstaller cannot produce a macOS app from Windows. See [VALIDATION.md](VALIDATION.md) for tested Windows scenarios and [PROGRESS.md](PROGRESS.md) for development checkpoints.
