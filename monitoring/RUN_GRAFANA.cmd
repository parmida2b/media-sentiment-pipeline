@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Group Pipeline Reddit Realtime Grafana v8

set "EXPECTED_BUILD=group-overlay-social-live-ui-20260814-08"
set "METRICS_TMP=%TEMP%\reddit_metrics_v8.txt"
set "HEALTH_TMP=%TEMP%\reddit_health_v8.json"
set "VM_TMP=%TEMP%\reddit_vm_v8.json"

 echo ========================================================================
 echo REDDIT REALTIME MONITORING STACK v8
 echo ========================================================================
 echo [check] Verifying Control Center identity, not just HTTP reachability...

curl.exe -fsS "http://127.0.0.1:8020/health" > "%HEALTH_TMP%" 2>nul
if errorlevel 1 goto :wrong_exporter
findstr /C:"%EXPECTED_BUILD%" "%HEALTH_TMP%" >nul
if errorlevel 1 goto :wrong_exporter

echo [OK] Control Center build identity matches v8.

curl.exe -fsS "http://127.0.0.1:8003/metrics" > "%METRICS_TMP%" 2>nul
if errorlevel 1 goto :wrong_exporter
findstr /C:"reddit_realtime_exporter_up" "%METRICS_TMP%" >nul
if errorlevel 1 goto :wrong_exporter
findstr /C:"reddit_realtime_build_info" "%METRICS_TMP%" >nul
if errorlevel 1 goto :wrong_exporter
findstr /C:"%EXPECTED_BUILD%" "%METRICS_TMP%" >nul
if errorlevel 1 goto :wrong_exporter

echo [OK] Port 8003 is the v8 Reddit realtime exporter.

echo [docker] Removing old monitoring containers...
docker rm -f group-pipeline-victoriametrics group-pipeline-grafana group-pipeline-grafana-renderer >nul 2>&1
docker compose down --remove-orphans >nul 2>&1
echo [docker] Recreating VictoriaMetrics/Grafana...
docker compose up -d --force-recreate
if errorlevel 1 goto :fail

echo [wait] Waiting for VictoriaMetrics to ingest reddit_realtime_exporter_up ...
set "VM_OK=0"
for /L %%I in (1,1,15) do (
  timeout /t 2 /nobreak >nul
  curl.exe -fsS "http://127.0.0.1:8428/api/v1/query?query=reddit_realtime_exporter_up" > "%VM_TMP%" 2>nul
  if not errorlevel 1 (
    findstr /C:"reddit_realtime_exporter_up" "%VM_TMP%" >nul
    if not errorlevel 1 (
      set "VM_OK=1"
      goto :vm_ready
    )
  )
  echo [wait] %%I/15 - metric not ingested yet...
)

:vm_ready
if "%VM_OK%"=="0" goto :vm_fail

echo [OK] VictoriaMetrics contains reddit_realtime_exporter_up.
type "%VM_TMP%"
echo.

echo [check] Grafana health...
for /L %%I in (1,1,10) do (
  curl.exe -fsS "http://127.0.0.1:8795/api/health" >nul 2>&1
  if not errorlevel 1 goto :grafana_ready
  timeout /t 1 /nobreak >nul
)
goto :grafana_fail

:grafana_ready
echo [OK] Grafana is reachable.
echo.
echo Metrics endpoint:        http://127.0.0.1:8003/metrics
echo VictoriaMetrics targets: http://127.0.0.1:8428/targets
echo VictoriaMetrics:         http://127.0.0.1:8428
echo Grafana:                 http://127.0.0.1:8795  ^(admin/admin^)
echo Dashboard:               Group Pipeline - Reddit Realtime Health
echo.
docker compose ps
pause
exit /b 0

:wrong_exporter
echo.
echo [ERROR] The process currently serving 8020/8003 is NOT the required v8 Control Center/exporter.
echo [ERROR] This was the exact cause of the previous Grafana "No data" state.
echo.
echo Required build: %EXPECTED_BUILD%
echo.
echo Fix:
echo   1. Run STOP_CONTROL_CENTER.cmd
 echo  2. Run START_CONTROL_CENTER.cmd from THIS v8 folder
 echo  3. Confirm http://127.0.0.1:8003/metrics contains:
 echo     reddit_realtime_exporter_up 1
 echo     reddit_realtime_build_info{build_id="%EXPECTED_BUILD%"} 1
 echo  4. Then run START_GRAFANA.cmd again
pause
exit /b 3

:vm_fail
echo.
echo [ERROR] Docker target may be UP, but VictoriaMetrics did not ingest the v8 Reddit metric within 30 seconds.
echo [ERROR] Open http://127.0.0.1:8428/targets and run CHECK_REDDIT_MONITORING.cmd.
pause
exit /b 4

:grafana_fail
echo [ERROR] VictoriaMetrics is receiving data, but Grafana health endpoint did not become ready.
pause
exit /b 5

:fail
echo.
echo [ERROR] Docker monitoring stack failed. Make sure Docker Desktop is running.
pause
exit /b 1
