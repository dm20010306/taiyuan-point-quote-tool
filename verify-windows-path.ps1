param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$DataRoot
)

try {
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    Write-Host "Launcher path: $resolved"
    if ($resolved.StartsWith('\\')) {
        Write-Host 'This is a UNC network path.'
        exit 1
    }
    $root = [System.IO.Path]::GetPathRoot($resolved)
    $driveType = [System.IO.DriveInfo]::new($root).DriveType
    if ($driveType -ne [System.IO.DriveType]::Fixed) {
        Write-Host "Drive type: $driveType"
        exit 1
    }
    if ($DataRoot) {
        $dataResolved = (Resolve-Path -LiteralPath $DataRoot -ErrorAction Stop).ProviderPath
        if ($dataResolved.StartsWith('\\')) {
            Write-Host 'Business data must be stored on a local fixed disk.'
            exit 1
        }
        $dataDrive = [System.IO.Path]::GetPathRoot($dataResolved)
        if ([System.IO.DriveInfo]::new($dataDrive).DriveType -ne [System.IO.DriveType]::Fixed) {
            Write-Host 'Business data must be stored on a local fixed disk.'
            exit 1
        }
        foreach ($relative in @('01_产品库\_品牌', '06_客户档案\智能图纸与报价', '09_附件')) {
            $required = Join-Path $dataResolved $relative
            if (-not (Test-Path -LiteralPath $required -PathType Container)) {
                Write-Host "Local business data is incomplete: $required"
                exit 1
            }
        }
    }
    exit 0
} catch {
    Write-Host "Local path check failed: $($_.Exception.Message)"
    exit 1
}
