# Build on the target OS; PyInstaller is not a cross-compiler.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / 'packaging' / 'entry.py')],
    pathex=[str(root)],
    binaries=[],
    datas=collect_data_files('whisper') + copy_metadata('openai-whisper'),
    hiddenimports=['whisper', 'tiktoken_ext.openai_public'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['auto_subtitle', 'ffmpeg', 'tkinter', 'matplotlib', 'IPython', 'pytest'],
    noarchive=False,
)
# The PySide6 hook pulls in Qt Virtual Keyboard even though this desktop app
# never uses it. Unlike our Qt UI modules, that module is GPL-3.0/commercial
# only. Do not redistribute its DLL/plugin in an MIT application.
_gpl_only_qt = {'qt6virtualkeyboard.dll', 'qtvirtualkeyboardplugin.dll'}
# CUDA wheel hooks also collect developer/profiling and auxiliary DLLs not
# needed for Whisper. NVIDIA's CUDA 12.8 EULA Attachment A does not explicitly
# name these files; do not ship them merely because they are in the wheel.
_unverified_cuda = {'nvperf_host.dll', 'cusolvermg64_11.dll',
                    'nvrtc64_120_0.alt.dll'}
# Keep nvJitLink_120_0.dll: official NVIDIA's 12.8 libnvjitlink redist
# contains that exact file, and PyTorch cannot load CUDA without it.
analysis.binaries = [entry for entry in analysis.binaries
                     if Path(entry[0]).name.lower() not in _gpl_only_qt | _unverified_cuda]
pyz = PYZ(analysis.pure)
gui = EXE(pyz, analysis.scripts, [], exclude_binaries=True,
          name='LocalCaption', console=False)
# Separate console worker keeps JSON stdout available in frozen builds.
# It is launched as a child, not as the user-facing application.
worker = EXE(pyz, analysis.scripts, [], exclude_binaries=True,
             name='LocalCaptionWorker', console=True)
app = COLLECT(gui, worker, analysis.binaries, analysis.datas, name='LocalCaption')
