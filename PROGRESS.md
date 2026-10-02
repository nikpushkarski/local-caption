# Work checkpoints

## Contract
Build a local replacement for the user's AutoSubtitleBackups script; eliminate
`auto_subtitle`, add a drag/drop Windows desktop GUI and executable packaging,
and keep the architecture ready for a later macOS build. Leave backups untouched.

## Iterations
1. Audit + repository checkpoint (complete).
2. Local subtitle core and regression tests (complete; 12 passing).
3. Offline processing worker, GUI, and safe output handling.
4. Packaging, integration tests, documentation, final checkpoint.

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
