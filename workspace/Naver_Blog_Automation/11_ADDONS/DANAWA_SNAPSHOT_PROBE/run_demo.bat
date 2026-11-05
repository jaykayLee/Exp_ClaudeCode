@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0tools\resolve_python.bat"
if not defined NB_PY_EXE (
  echo [FAIL] Python 3.11-3.13 not found.
  pause
  exit /b 2
)
"%NB_PY_EXE%" %NB_PY_ARGS% -m probe.snapshot_probe demo --out "%~dp0output\demo"
set "STATUS=%ERRORLEVEL%"
if "%STATUS%"=="0" if exist "%~dp0output\demo\snapshot_report.html" start "" "%~dp0output\demo\snapshot_report.html"
echo [RESULT] exit code %STATUS%. Synthetic data only.
pause
endlocal & exit /b %STATUS%
