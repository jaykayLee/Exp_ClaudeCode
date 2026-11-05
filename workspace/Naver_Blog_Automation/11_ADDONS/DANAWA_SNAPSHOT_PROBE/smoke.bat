@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0tools\resolve_python.bat"
if not defined NB_PY_EXE (
  echo [FAIL] Python 3.11-3.13 not found. Run baseline install.bat.
  pause
  exit /b 2
)
"%NB_PY_EXE%" %NB_PY_ARGS% -m unittest discover -s tests -v
set "STATUS=%ERRORLEVEL%"
echo [RESULT] tests exit code %STATUS%
pause
endlocal & exit /b %STATUS%
