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
set "LOCAL_HTML=%~1"
set "LOCAL_META=%~2"
if not defined LOCAL_HTML set /p "LOCAL_HTML=Saved HTML absolute path: "
if not defined LOCAL_META set /p "LOCAL_META=Completed metadata JSON absolute path: "
if not exist "%LOCAL_HTML%" (
  echo [FAIL] HTML file missing: %LOCAL_HTML%
  pause
  exit /b 2
)
if not exist "%LOCAL_META%" (
  echo [FAIL] metadata JSON missing: %LOCAL_META%
  pause
  exit /b 2
)
"%NB_PY_EXE%" %NB_PY_ARGS% -m probe.snapshot_probe inspect --html "%LOCAL_HTML%" --meta "%LOCAL_META%" --out "%~dp0output\manual"
set "STATUS=%ERRORLEVEL%"
if "%STATUS%"=="0" if exist "%~dp0output\manual\snapshot_report.html" start "" "%~dp0output\manual\snapshot_report.html"
echo [RESULT] exit code %STATUS%. Human review mandatory. No live crawling.
pause
endlocal & exit /b %STATUS%
