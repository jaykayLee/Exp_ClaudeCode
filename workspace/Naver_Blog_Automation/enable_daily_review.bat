@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\schedule.ps1"
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
