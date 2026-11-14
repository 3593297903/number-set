# Windows folder distribution. Two guarded executables, shared _internal payload.
from pathlib import Path
root=Path(SPECPATH).parent
a=Analysis([str(root/'main.py')],pathex=[str(root/'src')],binaries=[],datas=[],hiddenimports=[],hookspath=[],excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtPdf'])
# Qt 6.12 uses the Windows system ICU ABI. The host PATH also contains
# Poppler's differently versioned ICU; never distribute that foreign DLL.
a.binaries=[entry for entry in a.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll','icudt78.dll'}]
pyz=PYZ(a.pure)
tool=EXE(pyz,a.scripts,[],exclude_binaries=True,name='NumberTool',console=False,debug=False)
b=Analysis([str(root/'verify_main.py')],pathex=[str(root/'src')],binaries=[],datas=[],hiddenimports=[],hookspath=[],excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtPdf'])
b.binaries=[entry for entry in b.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll','icudt78.dll'}]
pyz_verify=PYZ(b.pure)
verify=EXE(pyz_verify,b.scripts,[],exclude_binaries=True,name='NumberVerify',console=True,debug=False)
coll=COLLECT(tool,verify,a.binaries,a.datas,b.binaries,b.datas,strip=False,upx=False,name='NumberTool')
