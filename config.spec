# Пример config.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
sys.path.append('C:\\path\\to\\your\\project')  # добавьте путь к корню вашего проекта

block_cipher = None

a = Analysis(['your_script.py'],
             pathex=['C:\\path\\to\\your\\project'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='your_executable',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

