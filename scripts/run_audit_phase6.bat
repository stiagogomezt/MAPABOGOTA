@echo off
setlocal
set "ROOT=%~dp0.."
if not "%QGIS_PYTHON_BAT%"=="" (
  call "%QGIS_PYTHON_BAT%" "%ROOT%\scripts\audit_phase6.py" %*
  exit /b %ERRORLEVEL%
)
for %%Q in ("C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat" "C:\Program Files\QGIS 4.2.2\bin\python-qgis.bat" "C:\Program Files\QGIS 4.0.0\bin\python-qgis.bat") do (
  if exist %%Q (
    call %%Q "%ROOT%\scripts\audit_phase6.py" %*
    exit /b %ERRORLEVEL%
  )
)
echo No se encontro python-qgis.bat. Configura QGIS_PYTHON_BAT.
exit /b 2
