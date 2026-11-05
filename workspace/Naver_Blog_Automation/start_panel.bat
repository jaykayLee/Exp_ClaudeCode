@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0.venv\Scripts\python.exe" goto missing
"%~dp0.venv\Scripts\python.exe" "%~dp0tools\server.py"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Action failed. Read the console and 09_LOGS.
pause
exit /b %RC%
:missing
echo Run install.bat first.
pause
exit /b 1
