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
pyz = PYZ(analysis.pure)
gui = EXE(pyz, analysis.scripts, [], exclude_binaries=True,
          name='LocalCaption', console=False)
# Separate console worker keeps JSON stdout available in frozen builds.
# It is launched as a child, not as the user-facing application.
worker = EXE(pyz, analysis.scripts, [], exclude_binaries=True,
             name='LocalCaptionWorker', console=True)
app = COLLECT(gui, worker, analysis.binaries, analysis.datas, name='LocalCaption')
