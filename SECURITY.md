# Trust boundaries

Removing auto_subtitle does **not** make this a dependency-free application or a
security sandbox. The GUI's separate worker is a responsiveness/cancellation
boundary, not an OS security boundary. Continue using Sandboxie if desired.

## Runtime dependencies

- PySide6 / Qt: native UI, drag/drop, font measurement and video preview decoding.
  Qt Multimedia brings its own native media backend/libraries into the app bundle;
  these are separate from the selected external FFmpeg processing tools.
- OpenAI Whisper, PyTorch (CPU-only or CUDA build), NumPy, tiktoken, numba/llvmlite
  and their dependencies: local inference. Versions and wheel hashes are in uv.lock.
  The optional CUDA edition bundles NVIDIA CUDA runtime libraries; the smaller
  CPU edition does not. Review third-party redistribution terms before sharing.
- External FFmpeg / FFprobe: native media parsing/encoding. Choose maintained,
  trusted binaries with libass/libx264. They are not bundled or auto-updated.
- A local Whisper checkpoint: choose a trusted official model; verify its SHA-256
  from an independently trusted source before use. The pinned Whisper loader uses
  torch.load(weights_only=True), but a model file is not inherently safe.

The app never imports auto_subtitle or ffmpeg-python. No code from those packages
was copied. Caption/layout behavior was adapted from the user's working script;
the SubRip serializer was written locally.

## Network and filesystem

There is no telemetry, remote API, update checker, or runtime model download.
Whisper receives an existing absolute checkpoint filename, not a model name.
FFmpeg input protocols are limited to `file,pipe`; URLs are not accepted via drag/drop.
Dependencies may contain network-capable code; this application does not enforce
an OS-wide network ban. Use a firewall/sandbox for an actual network guarantee.
UNC/network share paths are still filesystem paths and can access a network share.
Malicious media can exploit native codecs; a protocol allowlist is not a sandbox.

**Input previews decode selected media immediately**, before Start, in the GUI
process. Existing output media is decoded when Rendered video is selected. The
sample-caption view paints already decoded input frames; it writes no preview
video, subtitle file or modifications to the input. Previewing untrusted media carries native codec risk;
continue using an OS sandbox if required. The external worker's FFmpeg protocol
allowlist does not configure or sandbox Qt's separate multimedia decoder.
Whisper model loading and output generation still run only after Start.
GPU detection runs automatically in an isolated process at startup and after
FFmpeg path changes (or on Rescan). It queries Windows adapter names / NVIDIA
inventory, loads PyTorch, executes small CUDA kernels, and invokes the selected
FFmpeg for small synthetic hardware-encode tests. Thus selected tool binaries and
GPU drivers are exercised before Start. Choose trusted executables. The app does
not install drivers, download models, or change system GPU/driver settings.
Model/tool paths are saved in QSettings
(Windows registry: HKCU/Software/LocalCaption/LocalCaption). No automatic registry
startup entries, service, file association, shell integration or administrator
privileges are installed. Packaging produces unsigned executables.

Output MP4s are staged beside the destination and committed only on success.
Source files and edited SRTs are never deliberately overwritten. An existing output
video is replaced only with the user's permission. A generated SRT is kept on later
render failure. Forced termination while writing a *new* SRT may leave that new file
incomplete, but does not truncate pre-existing SRTs. Windows kill-on-close Job Objects
and POSIX process groups stop worker descendants on cancellation. An abrupt GUI
crash may leave a worker running; verify it has exited before cleaning job files.

Setup/build downloads dependencies; offline-runtime behavior is not an assertion
that the development/build process has no internet access. The application has
not undergone an independent security audit or adversarial media fuzzing.

## Distribution

Local Caption's own source is MIT-licensed; see LICENSE. Bundled components
keep their own licenses: see THIRD_PARTY_NOTICES.md and the `licenses/` folder
included with new builds. The Qt Multimedia preview backend includes LGPL
FFmpeg DLLs even though the FFmpeg/FFprobe *processing executables* are
external. The CUDA edition additionally contains NVIDIA libraries with separate
redistribution terms; review each build before sharing it. External tools and
model files remain the user's responsibility. Previously published binaries may
not contain these notices; rebuild before distributing them further.
