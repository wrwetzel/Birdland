# -*- mode: python ; coding: utf-8 -*-
# ---------------------------------------------------------------------
#   WRW 10 Mar 2022 - pyinstaller spec file for birdland
#   What a pain. After struggling for hours to duplicate results
#       of a toy test I changed name of source folder from bin to src
#       and things moved along. A few other rough edges related to
#       cwd of execution environment but all OK now.

#   WRW 15 Mar 2022 - More naming problems. This failed
#       when changed 'src' was 'birdland'. Resolved
#       when created symlink from birdland to src.

# ---------------------------------------------------------------------
#   /// from 10-Mar-2022 9:50 PM - Looks like this was last working
#       version before I started adding build-tables.py and check-offset.py
#       Abandoned that (see birdland-full.spec) in lieu of including
#       them as modules under birdland.py
#       ('src/birdland.pdf',                 'src'),

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
block_cipher = None

a = Analysis(['birdland_bootstrap.py'],
    pathex=['src'],
    binaries=[],
    datas=[
       ('src/Icons',                        'src/Icons'),
       ('src/Fullword-Match',               'src/Fullword-Match'),
       ('src/birdland.conf.proto',          'src'),
       ('src/ReadMe-Birdland.md',           '.'),
       ('src/Remove-Birdland.sh',           '.'),
       ('Package_Type_PyInstaller.txt',     'src'),
       ('Documentation',                    'Documentation'),
       ('Book-Lists',                       'Book-Lists'),
       ('Canonical',                        'Canonical'),
       ('Index-Sources',                    'Index-Sources'),
       ('Music-Index',                      'Music-Index'),
       ('YouTube-Index',                    'YouTube-Index'),
       ('ReadMe-PyInstaller.md',            '.' ),
       ('Install-From-PyInstaller.sh',      '.' ),
    ],
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='birdland',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None )

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='birdland')
