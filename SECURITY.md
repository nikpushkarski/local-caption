# Trust boundaries

Removing auto_subtitle does **not** make this a dependency-free application or a
security sandbox. The GUI's separate worker is a responsiveness/cancellation
boundary, not an OS security boundary. Continue using Sandboxie if desired.

## Runtime dependencies

- PySide6 / Qt: native UI, drag/drop, font measurement.
- OpenAI Whisper, PyTorch CPU, NumPy, tiktoken, numba/llvmlite and their dependencies:
  local inference. Versions and downloaded wheel hashes are in uv.lock.
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

Media is decoded only after Start. Model/tool paths are saved in QSettings
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

The source has no blanket public license assigned on the user's behalf. Before
publishing binaries, select a project license and review bundled dependency
licenses/notices (notably Qt/PySide6 LGPL/commercial terms and PyTorch/Whisper).
FFmpeg build licensing varies by enabled components. Keeping external binaries
external does not replace your obligation to review redistribution terms.
