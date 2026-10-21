$ErrorActionPreference = "SilentlyContinue"

# Ports 8000 and 5173 are reserved for this tool. Releasing their listeners is
# more reliable than matching process command lines across Python/Node versions.
foreach ($port in @(8000, 5173)) {
    Get-NetTCPConnection -State Listen -LocalPort $port | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force
    }
}

# Also stop detached child processes that no longer expose a listening socket.
$processes = Get-CimInstance Win32_Process | Where-Object {
    $command = $_.CommandLine
    $command -and (
        $command -match "backend\.app:app" -or
        ($command -match "TaiyuanPointQuote" -and $command -match "vite")
    )
}

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force
}

Start-Sleep -Seconds 1

$occupied = @()
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port) { $occupied += $port }
}
if ($occupied.Count -gt 0) {
    Write-Host "Unable to release ports: $($occupied -join ', ')" -ForegroundColor Red
    exit 1
}
