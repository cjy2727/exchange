# Build on Windows: python -m PyInstaller --noconfirm ExchangeStudio.spec
a = Analysis(['launcher.py'], pathex=[], binaries=[], datas=[('static', 'static')],
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ExchangeStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ExchangeStudio')
