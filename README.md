# Local Caption

Add hard subs to your videos and generate SRT files. Offline, with no subscriptions, no accounts, no telemetry, and other bullshit. 

The app has side-by-side video previews and can burn captions into an MP4, save an SRT, or add a selectable subtitle track.

> [!IMPORTANT]
> Windows app available. macOS support is work in progress.

## Prerequisites

- Trusted local **[FFmpeg + FFprobe](https://ffmpeg.org/download.html)** executables (`ffmpeg.exe`, `ffprobe.exe`) with libass and libx264 support. Not bundled.
- For transcription, a local **Whisper `.pt` model** from [OpenAI's official model download links](https://github.com/openai/whisper/blob/main/whisper/__init__.py#L17). Not bundled. I used `medium.pt` because it struck the right balance between accuracy and size.

The Windows app bundles its Python libraries; GPU support is optional.

## Get started on Windows

1. Download the **CPU edition** (~220 MB archive) from [GitHub Releases](https://github.com/nikpushkarski/local-caption/releases/latest). It works without an NVIDIA card and still supports hardware *video encoding* when FFmpeg does. For NVIDIA *transcription*, choose the larger **CUDA edition** (~2.4 GB download): get both numbered `.001` and `.002` parts and extract `.001` with [7-Zip](https://www.7-zip.org/). You only need **one** edition—do not combine their folders. Keep the extracted `LocalCaption` folder intact and run `LocalCaption.exe`. This is a portable, unsigned app—not an installer.
2. Select or drop a video onto the input preview.
3. Select the local FFmpeg/FFprobe executables and, if transcribing, the Whisper model listed above.
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

**GPU:** The app tests devices before offering them. The CPU edition cannot use CUDA for transcription, but both editions can use NVENC, Quick Sync or AMF for video encoding if your FFmpeg/driver supports it. The CUDA edition can also transcribe on a compatible NVIDIA card; it works on CPU too. Caption drawing remains on CPU. Unavailable choices are disabled.

The app never overwrites your input or an existing SRT. Replacing an output video requires confirmation. It can run inside Sandboxie if you prefer; drag-and-drop across a sandbox boundary may be blocked, so use Browse there. Selecting a video previews it immediately, so continue sandboxing untrusted media. See [SECURITY.md](SECURITY.md) for the trust boundaries.

## Build from source

Python 3.12 and [uv](https://docs.astral.sh/uv/) are recommended. **Run these commands from the project folder** (the one containing `pyproject.toml`):

```powershell
Set-Location -LiteralPath 'C:\Users\Nik Pushkarski\git\local-caption'

# Smaller CPU edition:
$env:UV_PROJECT_ENVIRONMENT = '.venv-cpu'
uv sync --locked --extra transcribe --extra build
powershell -NoProfile -File scripts\build-windows.ps1 -Variant cpu

# Or, for the larger CUDA edition, first clear the CPU environment override:
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
uv sync --locked --extra cuda --extra build
powershell -NoProfile -File scripts\build-windows.ps1 -Variant cuda
```

Run tests with `.venv-cpu\Scripts\python.exe -m unittest discover -s tests -v` (or `.venv\Scripts\python.exe` for CUDA). The two extras must not be combined.

If PowerShell blocks the build script, use `-ExecutionPolicy Bypass` on that PowerShell invocation only. Builds go in `dist\v<VERSION>-cpu\LocalCaption` or `dist\v<VERSION>\LocalCaption`. Build dependencies require internet; running the app does not. Before redistributing binaries, review bundled dependency licenses; see [SECURITY.md](SECURITY.md).

macOS packaging is not implemented or tested yet. PyInstaller cannot produce a macOS app from Windows. See [VALIDATION.md](VALIDATION.md) for tested Windows scenarios and [PROGRESS.md](PROGRESS.md) for development checkpoints.

## Clean up after building

Once you have saved the build you want **outside this repository**, run from the project folder:

```powershell
powershell -NoProfile -File scripts\reset-to-clone.ps1          # preview deletions
powershell -NoProfile -File scripts\reset-to-clone.ps1 -Apply   # type DELETE to confirm
```

This removes **every ignored and untracked file** (including all `dist/` builds, `.venv*` environments, `.tools/` downloads, and any media/models you placed here). It leaves Git history and tracked source intact. Move files you want to keep elsewhere first. It refuses to run if tracked files have uncommitted changes or an app/process is running from this folder; close them yourself and retry. If PowerShell blocks the script, add `-ExecutionPolicy Bypass` to the PowerShell invocation. Rebuilding later requires reinstalling dependencies.
