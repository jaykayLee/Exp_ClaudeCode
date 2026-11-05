@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0tools\resolve_python.bat"
if not defined NB_PY_EXE (
  echo [FAIL] Python 3.11-3.13 missing.
) else (
  echo [OK] Python launcher detected: %NB_PY_EXE% %NB_PY_ARGS%
  "%NB_PY_EXE%" %NB_PY_ARGS% --version
)
if exist "%~dp0..\..\00_PROJECT" (
  echo [OK] v1.0 workspace layout detected.
) else (
  if exist "%~dp0..\Naver_Blog_Automation\00_PROJECT" (
    echo [OK] Adjacent v1.0 workspace detected.
  ) else (
    echo [WARN] v1.0 workspace not found at common paths.
  )
)
if exist "%~dp0..\DANAWA_CSV_BRIDGE" (
  echo [INFO] v1.2 directory present (not tested for interface compatibility).
) else (
  echo [INFO] v1.2 directory not located at sibling path.
)
echo [INFO] This Add-on never calls Danawa or Naver remotely.
pause
endlocal
