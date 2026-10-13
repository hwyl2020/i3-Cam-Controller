@echo off
rem Launch Thermal Studio. Builds the SDK bridge the first time if needed.
setlocal
cd /d "%~dp0"
if not exist "app\bin\te_bridge.dll" (
    echo Building SDK bridge...
    call bridge\build.cmd || (echo Bridge build failed & pause & exit /b 1)
)
python -c "import PySide6, numpy, cv2" 2>nul || (
    echo Installing Python dependencies...
    python -m pip install -r requirements.txt || (pause & exit /b 1)
)
start "" pythonw app\main.py
