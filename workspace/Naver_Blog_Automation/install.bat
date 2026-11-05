@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\bootstrap.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Setup did not complete. Read the message and 09_LOGS.
pause
exit /b %RC%
