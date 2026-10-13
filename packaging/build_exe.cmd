@echo off
rem Builds dist\ThermalStudio\ThermalStudio.exe and dist\ThermalStudio-win64.zip
setlocal
cd /d "%~dp0.."
python -m pip install --quiet -r requirements.txt pyinstaller || exit /b 1
python packaging\make_icon.py || exit /b 1
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\ThermalStudio.spec || exit /b 1
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\ThermalStudio' -DestinationPath 'dist\ThermalStudio-win64.zip'" || exit /b 1
echo.
echo Built dist\ThermalStudio\ThermalStudio.exe
echo Zip:  dist\ThermalStudio-win64.zip
