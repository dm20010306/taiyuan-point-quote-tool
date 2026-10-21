param(
    [Parameter(Mandatory = $true)][string]$SourceDataPath,
    [Parameter(Mandatory = $true)][string]$DataRoot
)

$ErrorActionPreference = 'Stop'
$source = [System.IO.Path]::GetFullPath($SourceDataPath)
$target = [System.IO.Path]::GetFullPath($DataRoot)

try {
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        $parent = Split-Path -Parent $target
        New-Item -ItemType Directory -Path $parent -Force | Out-Null

        if (Test-Path -LiteralPath $source -PathType Container) {
            New-Item -ItemType Directory -Path $target | Out-Null
            & robocopy $source $target /E /COPY:DAT /DCOPY:DAT /R:2 /W:1 /NFL /NDL /NJH /NJS
            if ($LASTEXITCODE -ge 8) {
                throw "Copying existing tool data failed with robocopy exit code $LASTEXITCODE."
            }
        } else {
            New-Item -ItemType Directory -Path $target | Out-Null
        }
    }

    $required = @(
        '01_产品库\_品牌',
        '06_客户档案\智能图纸与报价',
        '09_附件\产品图片',
        '09_附件\品牌Logo',
        'uploads',
        'exports',
        'backups',
        'logs'
    )
    foreach ($relative in $required) {
        New-Item -ItemType Directory -Path (Join-Path $target $relative) -Force | Out-Null
    }

    Write-Host "Local business data folder: $target"
    exit 0
} catch {
    Write-Host "Local business data preparation failed: $($_.Exception.Message)"
    exit 1
}
