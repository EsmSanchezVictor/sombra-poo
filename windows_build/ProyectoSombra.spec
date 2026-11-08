# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

stage = Path(os.environ['SOMBRA_BUILD_STAGE']).resolve()
sys.path.insert(0, str(stage))
datas = []
binaries = []
hidden = ['main', 'tkinter', 'matplotlib.backends.backend_tkagg']
for package in ('core', 'services', 'ui'):
    hidden += collect_submodules(package)
for package in ('pvlib', 'pythermalcomfort', 'vtkmodules'):
    data, binary, imports = collect_all(package,
        filter_submodules=lambda name: not any(part in name.split('.') for part in ('qt', 'wx', 'test', 'tests')))
    datas += data
    binaries += binary
    hidden += imports
for distribution in ('numpy', 'pandas', 'opencv-python', 'openpyxl', 'matplotlib',
                     'Pillow', 'fpdf2', 'tzdata', 'pvlib', 'pythermalcomfort', 'vtk'):
    datas += copy_metadata(distribution)
for folder in ('data', 'test/imagen', 'docs', 'validacion', 'assest'):
    for source in (stage/folder).rglob('*'):
        if source.is_file():
            datas.append((str(source), source.relative_to(stage).parent.as_posix()))
for name in ('README.md', 'CHANGELOG.md'):
    if (stage/name).is_file():
        datas.append((str(stage/name), '.'))

a = Analysis([str(stage/'sombra_launcher.py')], pathex=[str(stage)],
             binaries=binaries, datas=datas, hiddenimports=sorted(set(hidden)),
             hookspath=[], runtime_hooks=[],
             excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pytest'],
             hooksconfig={'matplotlib': {'backends': ['TkAgg']}}, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ProyectoSombra',
          debug=False, strip=False, upx=False,
          console=os.environ.get('SOMBRA_BUILD_CONSOLE') == '1',
          disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ProyectoSombra')
