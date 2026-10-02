# Validated Windows checkpoint

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

The output is `dist/LocalCaption/LocalCaption.exe`, its worker exe, shared runtime
folder and documentation. Build artifacts and private development tooling are
intentionally not tracked in Git.

## Not yet validated / out of scope

- macOS/Linux builds, Apple Silicon, signing/notarization, installer/updater.
- Russian speech/automatic-language inference, GPU acceleration, long-form memory
  benchmarks and a broad codec/HDR/variable-frame-rate/device compatibility matrix.
- The packaged app running *inside* Sandboxie or cross-boundary drag/drop.
- Adversarial-media security audit or strict OS-level network isolation.
- Distribution-license clearance. See SECURITY.md before redistribution.
