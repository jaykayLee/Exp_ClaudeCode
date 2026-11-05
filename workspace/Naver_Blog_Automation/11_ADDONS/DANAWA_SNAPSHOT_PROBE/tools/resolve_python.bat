@echo off
rem Exports NB_PY_EXE (without quotes) and optional NB_PY_ARGS.
set "NB_PY_EXE="
set "NB_PY_ARGS="
if defined NB_WORKSPACE if exist "%NB_WORKSPACE%\.venv\Scripts\python.exe" (
  set "NB_PY_EXE=%NB_WORKSPACE%\.venv\Scripts\python.exe"
  goto :eof
)
if exist "%~dp0..\..\..\.venv\Scripts\python.exe" (
  set "NB_PY_EXE=%~dp0..\..\..\.venv\Scripts\python.exe"
  goto :eof
)
if exist "%~dp0..\..\Naver_Blog_Automation\.venv\Scripts\python.exe" (
  set "NB_PY_EXE=%~dp0..\..\Naver_Blog_Automation\.venv\Scripts\python.exe"
  goto :eof
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,14) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "NB_PY_EXE=py"
    set "NB_PY_ARGS=-3"
    goto :eof
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys;sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,14) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "NB_PY_EXE=python"
    goto :eof
  )
)
