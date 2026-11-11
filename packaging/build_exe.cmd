@echo off
rem Builds dist\ThermalStudio\ThermalStudio.exe (+ driver\) and dist\ThermalStudio-win64.zip
setlocal
cd /d "%~dp0.."
python -m pip install --quiet -r requirements.txt pyinstaller || exit /b 1
python packaging\make_icon.py || exit /b 1
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\ThermalStudio.spec || exit /b 1
rem The camera's USB driver ships beside the exe so the demo PC needs nothing else.
xcopy /e /i /q /y driver dist\ThermalStudio\driver >nul || exit /b 1
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\ThermalStudio' -DestinationPath 'dist\ThermalStudio-win64.zip'" || exit /b 1
echo.
echo Built dist\ThermalStudio\ThermalStudio.exe
echo Zip:  dist\ThermalStudio-win64.zip
