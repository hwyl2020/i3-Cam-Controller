# PyInstaller spec for Thermal Studio (one-folder build, windowed).
# Build with packaging\build_exe.cmd
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
APP = os.path.join(ROOT, "app")
BIN = os.path.join(APP, "bin")
SYS32 = os.path.join(os.environ["SystemRoot"], "System32")

# te_bridge + i3system SDK runtime (the OpenCV 2.4.9 DLLs in app\bin are not used).
sdk_dlls = ["te_bridge.dll", "i3system_TE_x64.dll", "i3system_USB_DLL_V2_2_x64.dll",
            "i3system_imgproc_x64.dll", "i3system_imgproc_impl_x64.dll"]
# The SDK needs the VC++ 2015-2022 runtime incl. MFC; bundle it app-locally so the
# exe also runs on PCs without the Visual C++ Redistributable.
vc_dlls = ["mfc140u.dll", "msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"]

binaries = [(os.path.join(BIN, d), "bin") for d in sdk_dlls]
binaries += [(os.path.join(SYS32, d), "bin") for d in vc_dlls]

a = Analysis(
    [os.path.join(APP, "main.py")],
    pathex=[APP],
    binaries=binaries,
    datas=[(os.path.join(APP, "ui", "assets"), os.path.join("ui", "assets"))],
    hiddenimports=[],
    excludes=["tkinter", "matplotlib", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf",
              "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ThermalStudio",
    icon=os.path.join(SPECPATH, "ThermalStudio.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ThermalStudio", upx=False)
