# Work checkpoints

## Contract
Build a local replacement for the user's AutoSubtitleBackups script; eliminate
`auto_subtitle`, add a drag/drop Windows desktop GUI and executable packaging,
and keep the architecture ready for a later macOS build. Leave backups untouched.

## Iterations
1. Audit + repository checkpoint (complete).
2. Local subtitle core and regression tests (complete; 12 passing).
3. Offline processing worker, GUI, and safe output handling (complete; 20 tests passing).
   Real FFmpeg burn/mux integration verified, including silent video, Unicode/apostrophe
   paths, first-frame caption pixels, and unchanged edited SRT. Qt drag/drop events tested.
4. Packaging, cancellation/transcription tests, documentation (complete; final validation current).
   24 tests passing, including Qt-driven source and frozen worker lifecycles.
   Windows one-folder exe built; native desktop launch/close verified (exit 0).
   Frozen worker burn, mux, and actual medium-model transcription+burn all passed.
   Official medium SHA256 verified read-only before inference:
   345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1.
   Speech was generated locally using Windows System.Speech. No model downloaded.
   Native screenshot reviewed. Found Windows offscreen Qt font discovery returns
   box glyphs; switched the windowless worker to native desktop font discovery.
   Rebuild + final regression required after that correction.

## Behavioral changes
- Five explicit actions replace the nested console prompts. Mux takes the desired
  existing video as input and writes a separate MP4 (source is never replaced).
- GUI shows elapsed time, activity and confirmed transcription checkpoints instead
  of a history-based estimated ETA. This avoids presenting guesses as progress.
- Windows Job Object ties FFmpeg lifetime to worker lifetime; POSIX uses process groups.
- GUI owns staging directory on the output volume so worker cancellation can be cleaned.
- Atomic no-clobber output publication uses hard links (fails safely if unsupported).

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
