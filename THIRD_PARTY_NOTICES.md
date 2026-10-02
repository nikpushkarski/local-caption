# Third-party notices (Windows distributions)

Local Caption's own code is MIT-licensed; see `LICENSE`. Its portable Windows
builds also contain independently licensed software. A license for this project
does **not** change the licenses of those components.

- **Qt 6.10.2 / PySide6 6.10.2 / shiboken6**: used under the LGPL-3.0 option
  (not the commercial or GPL option). See `licenses/LGPL-3.0-only.txt` and
  `licenses/GPL-3.0-only.txt` (the LGPL v3 supplements GPL v3). Qt and PySide
  copyrights and additional module notices remain with their respective
  projects. Sources: [Qt 6.10.2](https://download.qt.io/archive/qt/6.10/6.10.2/),
  [Qt for Python 6.10.2 source](https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.10.2).
  The included Qt DLLs, plugins and PySide binaries are separate files under
  `_internal/PySide6/`. You may replace these with ABI-compatible modified
  versions for debugging changes to the LGPL-covered libraries. No part of
  this project's license prohibits reverse engineering for that purpose.
  We exclude the unused GPL-only Qt Virtual Keyboard module and its plugin
  from new builds.
- **Qt Multimedia's FFmpeg 7.1.2 libraries**: the included
  `_internal/PySide6/avcodec-61.dll`, `avformat-61.dll`, `avutil-59.dll`,
  `swresample-5.dll` and `swscale-8.dll` are from Qt's LGPL-2.1-or-later
  build (verified with `avcodec_license` and `avcodec_configuration`). See
  `licenses/LGPL-2.1-only.txt` and [FFmpeg 7.1.2 source](https://github.com/FFmpeg/FFmpeg/tree/n7.1.2).
  These are **not** the external `ffmpeg.exe` / `ffprobe.exe` the user selects
  for processing; those executables and their licensing depend on the user's
  chosen build and are not included here.
- **PyTorch 2.10.0**: BSD-3-Clause; its wheel's `LICENSE` includes additional
  third-party terms, and `NOTICE` includes required attributions. Both are
  copied verbatim to `licenses/python/torch-*/` at build time.
- **OpenAI Whisper 20250625**: MIT; the wheel's `LICENSE` is copied to
  `licenses/python/openai-whisper-*/` at build time. Model files are external.
- **Other Python dependencies**: the build copies original wheel license and
  notice files to `licenses/python/<package>-<version>/` (including NumPy and
  its subcomponents). This includes build-only packages if installed in the
  build environment; it does not claim they are all part of the runtime.
- **CUDA edition only**: PyTorch's CUDA wheel also packages NVIDIA CUDA,
  cuBLAS, cuDNN and other NVIDIA DLLs under `_internal/torch/lib/`.
  PyTorch's wheel `LICENSE`/`NOTICE` are copied, but NVIDIA components have
  [separate CUDA 12.8 redistribution terms](https://docs.nvidia.com/cuda/archive/12.8.0/eula/index.html)
  and [cuDNN 9.10.2 terms](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html).
  [CUDA_REDISTRIBUTION.md](CUDA_REDISTRIBUTION.md) inventories the actual
  audited DLLs, excludes three unneeded/unlisted ones, and records the
  remaining `nvJitLink` filename ambiguity. That audit applies only to the
  **newly rebuilt** CUDA distribution, not the withdrawn older release.
  The MIT license and PyTorch BSD notice do not license NVIDIA software.

The license texts in `licenses/` for GNU components come from the
[SPDX license list](https://github.com/spdx/license-list-data). License and
notice files under `licenses/python/` are copied directly from the pinned
installed wheels when the release is built. Before releasing an updated build,
re-audit its actual bundle and licensing; wheel contents can change.
