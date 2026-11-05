@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
    py -3 tools\verify_handoff.py
    goto end
)
where python >nul 2>&1
if not errorlevel 1 (
    python tools\verify_handoff.py
    goto end
)
echo Python was not found. Use the cloud Python terminal or install the workspace first.
:end
pause
endlocal
