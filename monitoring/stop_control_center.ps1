param([switch]$Quiet)

$targetPorts = @(8020, 8003)
$stopped = @()
$skipped = @()

foreach ($port in $targetPorts) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $pidValue = [int]$listener.OwningProcess
        if ($stopped -contains $pidValue -or $skipped -contains $pidValue) { continue }
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction Stop
            $name = [string]$proc.Name
            $cmd = [string]$proc.CommandLine
            $isPython = $name -match '^python(?:w)?\.exe$'
            $isOurControlCenter = $cmd -match 'control_center\.py'
            if ($isPython -and $isOurControlCenter) {
                if (-not $Quiet) { Write-Host "[cleanup] Stopping old Control Center PID $pidValue on port $port" }
                Stop-Process -Id $pidValue -Force -ErrorAction Stop
                $stopped += $pidValue
            } else {
                if (-not $Quiet) {
                    Write-Host "[cleanup] Port $port is owned by PID $pidValue ($name); not touching unrelated process."
                    Write-Host "[cleanup] CommandLine: $cmd"
                }
                $skipped += $pidValue
            }
        } catch {
            if (-not $Quiet) { Write-Host "[cleanup] Could not inspect/stop PID $pidValue : $($_.Exception.Message)" }
            $skipped += $pidValue
        }
    }
}

Start-Sleep -Milliseconds 800
if (-not $Quiet) {
    Write-Host "[cleanup] Stopped process count: $($stopped.Count)"
}
if ($skipped.Count -gt 0) { exit 2 }
exit 0
