# -*- mode: python ; coding: utf-8 -*-
# ---------------------------------------------------------------------
#   WRW 10 Mar 2022 - pyinstaller spec file for birdland
#   What a pain. After struggling for hours to duplicate results
#       of a toy test I changed name of source folder from bin to src
#       and things moved along. A few other rough edges related to
#       cwd of execution environment but all OK now.
# ---------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules

collect_all = False

hiddenimports = []
#   This is from --collect-submodules bin \
#       but works without it.
#       t = collect_submodules('src')
#       hiddenimports += [ x for x in t if ',' not in x ]

#   datas:
#       ( file or folder in system now, folder to contain item at run time )

block_cipher = None

print( "/// Analysis startup" )

a = Analysis(['startup.py'],
    pathex=['src/birdland'],
    binaries=[],
    datas=[
       ('src/birdland',                     'birdland'),
       ('src/birdland/Icons',               'birdland/Icons'),
       ('src/birdland/Fullword-Match',      'birdland/Fullword-Match'),
       ('src/birdland/birdland.conf.proto', 'birdland/birdland.conf.proto'),
       ('src/birdland/birdland.pdf',        'birdland/birdland.pdf'),
       ('src/birdland/ReadMe.txt',          'birdland/ReadMe.txt'),
       ('src/Book-Lists',                   'Book-Lists'),
       ('src/Canonical',                    'Canonical'),
       ('src/Index-Sources',                'Index-Sources'),
       ('src/Music-Index',                  'Music-Index'),
       ('src/YouTube-Index',                'YouTube-Index')
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

# -------------------------------------------------------------------------------

print( "/// Analysis check_offsets" )

check_offsets_a = Analysis(['src/birdland/check_offsets.py'],
    pathex=['src/birdland'],
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

print( "/// Analysis build_tables" )

build_tables_a = Analysis(['src/birdland/build_tables.py'],
    pathex=['src/birdland'],
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

# -----------------------------------------------------------
#   (analysis_object, script_name_of_analyzed_app (no .py), executable_name )

print( "/// Merge" )

MERGE( 
        (a, 'startup',      'startup' ),
        (build_tables_a,    'build_tables',  'build_tables'),
        (check_offsets_a,   'check_offsets', 'check_offsets')
    )

# -----------------------------------------------------------

print( "/// pyz/exe/coll startup" )

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

if not collect_all:
    coll = COLLECT(exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='birdland')

# -----------------------------------------------------------

print( "/// pyz/exe/coll build_tables" )

build_tables_pyz = PYZ(build_tables_a.pure, build_tables_a.zipped_data,
    cipher=block_cipher)

build_tables_exe = EXE(build_tables_pyz,
    build_tables_a.scripts,
    [],
    exclude_binaries=True,
    name='build-tables',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None )

if not collect_all:
    build_tables_coll = COLLECT(build_tables_exe,
        build_tables_a.binaries,
        build_tables_a.zipfiles,
        build_tables_a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='build-tables')

# -----------------------------------------------------------

print( "/// pyz/exe/coll check_offsets" )

check_offsets_pyz = PYZ(check_offsets_a.pure, check_offsets_a.zipped_data,
    cipher=block_cipher)

check_offsets_exe = EXE(check_offsets_pyz,
    check_offsets_a.scripts,
    [],
    exclude_binaries=True,
    name='check-offsets',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None )

if not collect_all:
    check_offsets_coll = COLLECT(check_offsets_exe,
        check_offsets_a.binaries,
        check_offsets_a.zipfiles,
        check_offsets_a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='check-offsets')


# -----------------------------------------------------------
#   WRW 11 Mar 2022 - Trying to collect all together

if collect_all:
    print( "/// Full collection" )

    coll = COLLECT(exe,
        a.binaries,
        a.zipfiles,
        a.datas,
    
        build_tables_a.binaries,
        build_tables_a.zipfiles,
        build_tables_a.datas,
    
        check_offsets_a.binaries,
        check_offsets_a.zipfiles,
        check_offsets_a.datas,
    
        strip=False,
        upx=True,
        upx_exclude=[],
        name='birdland'
    )

# -----------------------------------------------------------
print( "/// Done" )

