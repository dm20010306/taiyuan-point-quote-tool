param(
    [Parameter(Mandatory = $true)][string]$ExpectedVersion,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "SilentlyContinue"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$lastApiError = "API has not responded yet."
$lastWebError = "Web app has not responded yet."

while ((Get-Date) -lt $deadline) {
    try {
        $api = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/version" -TimeoutSec 2
        $lastApiError = "API responded with version $($api.version)."
        if ($api.version -and $api.version -ne $ExpectedVersion) {
            Write-Host "Version mismatch: expected $ExpectedVersion, API returned $($api.version)." -ForegroundColor Red
            exit 2
        }
    } catch {
        $lastApiError = $_.Exception.Message
        $api = $null
    }

    try {
        $web = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173/?version=$ExpectedVersion" -TimeoutSec 2
        $lastWebError = "Web app responded with HTTP $($web.StatusCode)."
    } catch {
        $lastWebError = $_.Exception.Message
        $web = $null
    }

    if ($api.version -eq $ExpectedVersion -and $web.StatusCode -eq 200) {
        Write-Host "PointQuote V$ExpectedVersion is ready and version-checked." -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Seconds 1
}

Write-Host "PointQuote did not become ready within $TimeoutSeconds seconds." -ForegroundColor Red
Write-Host "Last API result: $lastApiError" -ForegroundColor Yellow
Write-Host "Last web result: $lastWebError" -ForegroundColor Yellow
exit 3
