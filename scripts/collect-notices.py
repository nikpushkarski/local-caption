"""Copy installed wheel notices into a Windows build; run with its build Python."""
import ctypes
import importlib.metadata as metadata
import os
from pathlib import Path
import re
import shutil
import sys


def main() -> None:
    app = Path(sys.argv[1]).resolve()
    variant = sys.argv[2]
    if variant not in {'cpu', 'cuda'} or not (app / 'LocalCaption.exe').is_file():
        raise SystemExit('Pass an existing build folder and cpu or cuda')
    target = app / 'licenses' / 'python'
    target.mkdir(parents=True, exist_ok=True)
    for dist in metadata.distributions():
        name = dist.metadata.get('Name', '')
        if not name or name.lower() == 'local-caption':
            continue
        folder = re.sub(r'[^a-zA-Z0-9.+_-]', '_', f'{name}-{dist.version}')
        for entry in dist.files or ():
            parts = Path(str(entry)).parts
            if len(parts) < 2 or not parts[0].endswith('.dist-info'):
                continue
            if not any(word in parts[-1].lower() for word in ('license', 'licence', 'copying', 'notice')):
                continue
            if parts[-1] == 'LicenseRef-Qt-Commercial.txt':
                continue  # The distributed build uses the open-source LGPL option.
            source = Path(dist.locate_file(entry))
            if source.is_file():
                dest = target / folder / Path(*parts[1:])
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
    required = ('torch', 'openai-whisper')
    for name in required:
        if not any((target / f'{name}-{metadata.version(name)}').rglob('*LICENSE*')):
            raise RuntimeError(f'No wheel license for {name}')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('CPython runtime license missing')
    python_target = target / f'CPython-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
    python_target.mkdir(exist_ok=True)
    shutil.copyfile(python_license, python_target / 'LICENSE.txt')

    qt = app / '_internal' / 'PySide6'
    for forbidden in ('Qt6VirtualKeyboard.dll', 'qtvirtualkeyboardplugin.dll'):
        if list(qt.rglob(forbidden)):
            raise RuntimeError(f'GPL-only Qt Virtual Keyboard was bundled: {forbidden}')
    if os.name == 'nt':
        with os.add_dll_directory(str(qt)):
            codec = ctypes.WinDLL(str(qt / 'avcodec-61.dll'))
            codec.avcodec_license.restype = ctypes.c_char_p
            license_name = codec.avcodec_license().decode('ascii')
            if license_name != 'LGPL version 2.1 or later':
                raise RuntimeError(f'Unexpected bundled FFmpeg license: {license_name}')
    cuda_dll = app / '_internal' / 'torch' / 'lib' / 'cudart64_12.dll'
    if cuda_dll.is_file() != (variant == 'cuda'):
        raise RuntimeError(f'CUDA runtime mismatch for {variant} build')
    print(f'Bundled original wheel/CPython notices and audited {variant} DLLs in {app}')


if __name__ == '__main__':
    main()
