# run_youtube_incremental_weekly.ps1 — weekly-run wrapper for
# src/ingestion/youtube_extract.py (Parmida)
#
# youtube_extract.py used to be split into a v1 (youtube_extract.py) and a
# v2 (youtube_extract_incremental.py) script; they were consolidated into
# one file (see docs/decision_log.md) — this wrapper now points at that
# single script instead of the retired _incremental one.
#
# Meant to be registered as a Windows Task Scheduler action (see
# docs/setup.md, "اجرای خودکار هفتگی"). The Python script itself is
# idempotent/incremental (safe to run more or less often than weekly, or
# to re-run after a failure) — this wrapper's job is just logging +
# a non-zero exit code on failure so Task Scheduler's history shows it.
#
# Manual run: powershell -File scripts\run_youtube_incremental_weekly.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "outputs\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$LogFile = Join-Path $LogDir "youtube_incremental_$Timestamp.log"

# Override by setting $env:PYTHON_EXE before calling this script if you use
# a virtualenv/conda env instead of the system python on PATH.
$PythonExe = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$ScriptPath = Join-Path $ProjectRoot "src\ingestion\youtube_extract.py"

Write-Output "[$Timestamp] Starting incremental YouTube collection..." | Tee-Object -FilePath $LogFile
Write-Output "Project root: $ProjectRoot" | Tee-Object -FilePath $LogFile -Append
Write-Output "Python: $PythonExe" | Tee-Object -FilePath $LogFile -Append
Write-Output "----------------------------------------" | Tee-Object -FilePath $LogFile -Append

Push-Location $ProjectRoot
try {
    & $PythonExe $ScriptPath 2>&1 | Tee-Object -FilePath $LogFile -Append
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($ExitCode -ne 0) {
    Write-Output "[FAILED] exit code $ExitCode — see $LogFile" | Tee-Object -FilePath $LogFile -Append
    exit $ExitCode
}

Write-Output "[OK] finished — see $LogFile"
exit 0
