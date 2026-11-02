@echo off
setlocal
set "ROOT=%~dp0.."
if not "%BLENDER_EXE%"=="" (
  "%BLENDER_EXE%" -b --python-exit-code 1 -P "%ROOT%\blender\build_scene.py"
  exit /b %ERRORLEVEL%
)
if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" (
  "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python-exit-code 1 -P "%ROOT%\blender\build_scene.py"
  exit /b %ERRORLEVEL%
)
echo No se encontro Blender. Configura BLENDER_EXE.
exit /b 2
