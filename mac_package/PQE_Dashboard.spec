# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

streamlit_datas = collect_data_files('streamlit') + copy_metadata('streamlit')
plotly_datas = collect_data_files('plotly') + copy_metadata('plotly')
pandas_datas = copy_metadata('pandas')
openpyxl_datas = copy_metadata('openpyxl')

datas = [
    ('../pqe_phase1_ui.py', '.'),
    ('../pqe_phase1_mvp.py', '.'),
]
datas += streamlit_datas + plotly_datas + pandas_datas + openpyxl_datas

hiddenimports = []
hiddenimports += collect_submodules('streamlit')
hiddenimports += collect_submodules('plotly')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += [
    'pandas',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.np_datetime',
]

block_cipher = None


a = Analysis(
    ['pqe_desktop_launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PQE Dashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PQE Dashboard',
)
app = BUNDLE(
    coll,
    name='PQE Dashboard.app',
    icon=None,
    bundle_identifier='com.nordbo.pqe-dashboard',
    info_plist={
        'CFBundleDisplayName': 'PQE 数据分析平台',
        'CFBundleName': 'PQE Dashboard',
        'NSHighResolutionCapable': 'True',
    },
)
