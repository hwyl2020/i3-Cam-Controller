@echo off
rem Builds te_bridge.dll (x64) against the i3system SDK in sdk\ and writes it to
rem app\bin (set OUT=... to build somewhere else). The SDK runtime DLLs already
rem live in app\bin.
setlocal
set ROOT=%~dp0..
set SDK=%ROOT%\sdk
if not defined OUT set OUT=%ROOT%\app\bin

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "usebackq delims=" %%i in (`call "%VSWHERE%" -latest -products * -property installationPath`) do set "VS=%%i"
if not defined VS (echo Visual Studio with C++ tools not found & exit /b 1)
call "%VS%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>nul || exit /b 1

if not exist "%OUT%" mkdir "%OUT%"
pushd "%~dp0"
cl /nologo /LD /EHsc /O2 /MD /W3 /D_WINDOWS /DUNICODE /D_UNICODE ^
   /I"%SDK%\include" te_bridge.cpp ^
   /link /LIBPATH:"%SDK%\lib" i3system_TE_x64.lib i3system_imgproc_x64.lib ^
   /OUT:"%OUT%\te_bridge.dll" || (popd & exit /b 1)
del /q te_bridge.obj te_bridge.exp te_bridge.lib "%OUT%\te_bridge.exp" "%OUT%\te_bridge.lib" 2>nul
popd
echo Built %OUT%\te_bridge.dll
