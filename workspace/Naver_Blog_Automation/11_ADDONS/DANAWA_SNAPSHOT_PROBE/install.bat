@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "SOURCE=%~dp0"
set "TARGET_ROOT=%~dp0..\Naver_Blog_Automation"
if defined NB_WORKSPACE set "TARGET_ROOT=%NB_WORKSPACE%"
if not exist "%TARGET_ROOT%\00_PROJECT" (
  echo [INFO] Baseline folder not found next to this Add-on.
  echo Enter the existing v1.0 workspace ROOT containing 00_PROJECT and 11_ADDONS.
  set /p "TARGET_ROOT=Workspace path: "
)
if not exist "%TARGET_ROOT%\00_PROJECT" (
  echo [FAIL] Baseline not found. Run the v1.0 install.bat first.
  pause
  exit /b 2
)
if not exist "%TARGET_ROOT%\11_ADDONS" (
  echo [FAIL] Missing 11_ADDONS folder in workspace.
  pause
  exit /b 2
)
set "DEST=%TARGET_ROOT%\11_ADDONS\DANAWA_SNAPSHOT_PROBE"
if exist "%DEST%" (
  echo [HOLD] %DEST% already exists. No overwrite performed.
  echo Compare the version/manifest manually before merging.
  pause
  exit /b 3
)
set "NB_WORKSPACE=%TARGET_ROOT%"
call "%SOURCE%tools\resolve_python.bat"
if not defined NB_PY_EXE (
  echo [FAIL] Python 3.11-3.13 not found. Use workspace install.bat first.
  pause
  exit /b 4
)
xcopy "%SOURCE%*" "%DEST%\" /E /I /H /Y >nul
if errorlevel 1 (
  echo [FAIL] Copy failed. Check file permissions.
  pause
  exit /b 5
)
echo [OK] Installed Add-on only: %DEST%
echo [NEXT] Run %DEST%\smoke.bat and run_demo.bat.
pause
endlocal
