@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Reddit Monitoring Diagnostics v8
set "EXPECTED_BUILD=group-overlay-social-live-ui-20260814-08"
set "TMP1=%TEMP%\reddit_diag_health.json"
set "TMP2=%TEMP%\reddit_diag_metrics.txt"
set "TMP3=%TEMP%\reddit_diag_vm.json"

 echo ========================================================================
 echo REDDIT MONITORING DIAGNOSTICS v8
 echo Expected build: %EXPECTED_BUILD%
 echo ========================================================================

 echo [1/5] Control Center identity...
curl.exe -fsS "http://127.0.0.1:8020/health" > "%TMP1%" 2>nul
if errorlevel 1 (
  echo [FAIL] Control Center is not reachable on 8020.
) else (
  type "%TMP1%"
  echo.
  findstr /C:"%EXPECTED_BUILD%" "%TMP1%" >nul
  if errorlevel 1 (echo [FAIL] WRONG Control Center build is running.) else (echo [OK] Correct v8 Control Center.)
)

 echo.
 echo [2/5] Metrics endpoint identity and Reddit series...
curl.exe -fsS "http://127.0.0.1:8003/metrics" > "%TMP2%" 2>nul
if errorlevel 1 (
  echo [FAIL] Port 8003 is unreachable.
) else (
  findstr /C:"reddit_realtime_build_info" /C:"reddit_realtime_exporter_up" /C:"reddit_realtime_parent_posts" /C:"reddit_realtime_raw_json_files" /C:"reddit_realtime_comments_live" "%TMP2%"
  findstr /C:"reddit_realtime_build_info" "%TMP2%" >nul
  if errorlevel 1 (echo [FAIL] Port 8003 is not serving realtime build identity.) else (
    findstr /C:"%EXPECTED_BUILD%" "%TMP2%" >nul
    if errorlevel 1 (echo [FAIL] Port 8003 is serving OLD/WRONG metrics.) else (echo [OK] Correct v8 metrics exporter.)
  )
)

 echo.
 echo [3/5] Docker / VictoriaMetrics target...
docker compose ps
 echo.
 echo Target page: http://127.0.0.1:8428/targets

 echo.
 echo [4/5] VictoriaMetrics query for v8 Reddit exporter...
curl.exe -fsS "http://127.0.0.1:8428/api/v1/query?query=reddit_realtime_exporter_up" > "%TMP3%" 2>nul
if errorlevel 1 (
  echo [FAIL] VictoriaMetrics query endpoint failed.
) else (
  type "%TMP3%"
  echo.
  findstr /C:"reddit_realtime_exporter_up" "%TMP3%" >nul
  if errorlevel 1 (echo [FAIL] Target may be UP, but v8 Reddit metric is NOT stored.) else (echo [OK] VictoriaMetrics has v8 Reddit metrics.)
)

 echo.
 echo [5/5] Grafana health...
curl.exe -fsS "http://127.0.0.1:8795/api/health"
if errorlevel 1 echo [FAIL] Grafana is not reachable on 8795.

echo.
echo Useful URLs:
echo   Control Center: http://127.0.0.1:8020
echo   Metrics:        http://127.0.0.1:8003/metrics
echo   Targets:        http://127.0.0.1:8428/targets
echo   Grafana:        http://127.0.0.1:8795
pause
