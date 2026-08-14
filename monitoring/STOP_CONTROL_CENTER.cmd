@echo off
setlocal
cd /d "%~dp0"
title Stop Group Pipeline Control Center
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_control_center.ps1"
echo.
echo If no unrelated process owns ports 8020/8003, the old Control Center is now stopped.
pause
