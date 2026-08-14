@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Group Pipeline Control Center v8

set "EXPECTED_BUILD=group-overlay-social-live-ui-20260814-08"
set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "DEPS_MARKER=%VENV_DIR%\.deps_ready"
set "HEALTH_TMP=%TEMP%\group_pipeline_health.json"
set "METRICS_TMP=%TEMP%\group_pipeline_metrics.txt"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
echo ========================================================================
echo GROUP PIPELINE CONTROL CENTER - REDDIT OBSERVABILITY v8
echo Expected build: %EXPECTED_BUILD%
echo Project: %CD%
echo Virtual environment: %VENV_DIR%
echo ========================================================================

REM --- Check Port 8020 ---
curl.exe -fsS "http://127.0.0.1:8020/health" > "%HEALTH_TMP%" 2>nul
if not errorlevel 1 (
  findstr /C:"%EXPECTED_BUILD%" "%HEALTH_TMP%" >nul
  if not errorlevel 1 (
    echo [OK] Control Center is already running on port 8020.
    echo [OK] Open: http://127.0.0.1:8020
    pause
    exit /b 0
  )

  findstr /C:"group-overlay" "%HEALTH_TMP%" >nul
  if not errorlevel 1 (
    echo [cleanup] Older Control Center detected. Stopping Python processes.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_control_center.ps1" -Quiet
    timeout /t 2 /nobreak >nul
  ) else (
    echo [ERROR] Port 8020 is occupied by another service.
    goto :ports_busy
  )
)

REM --- Check Port 8003 ---
curl.exe -fsS "http://127.0.0.1:8003/metrics" > "%METRICS_TMP%" 2>nul
if not errorlevel 1 (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_control_center.ps1" -Quiet
  timeout /t 2 /nobreak >nul
)

powershell.exe -NoProfile -Command "$p=Get-NetTCPConnection -State Listen -LocalPort 8020,8003 -ErrorAction SilentlyContinue; if($p){exit 1}else{exit 0}"
if errorlevel 1 goto :ports_busy

REM --- Create Virtual Environment ---
if not exist "%PYTHON_EXE%" (
  echo [setup] Creating virtual environment in .venv
  py -3.12 -m venv "%VENV_DIR%"
  if errorlevel 1 (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
  )
)

REM --- Install Requirements ---
if not exist "%DEPS_MARKER%" (
  echo [setup] Upgrading pip
  "%PYTHON_EXE%" -m pip install --upgrade pip
  if errorlevel 1 goto :fail

  echo [setup] Step 1 of 2: Installing base pipeline requirements
  "%PYTHON_EXE%" -m pip install -r "..\requirements.txt"
  if errorlevel 1 goto :fail

  echo [setup] Step 2 of 2: Installing monitoring requirements
  "%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 goto :fail

  type nul > "%DEPS_MARKER%"
)

REM --- Smoke Test & Launch ---
echo [check] Rendering Control Center routes
"%PYTHON_EXE%" smoke_test_overlay.py
if errorlevel 1 goto :fail

echo.
echo [start] Web UI:  http://127.0.0.1:8020
echo [start] Metrics: http://127.0.0.1:8003/metrics
echo.
"%PYTHON_EXE%" control_center.py
set ERR=%ERRORLEVEL%
echo.
echo Control Center stopped with exit code %ERR%.
pause
exit /b %ERR%

:ports_busy
echo.
echo [ERROR] Ports 8020 and 8003 are still occupied.
pause
exit /b 2

:fail
echo.
echo [ERROR] Setup or start failed.
echo [ERROR] Virtual environment path: %VENV_DIR%
pause
exit /b 1