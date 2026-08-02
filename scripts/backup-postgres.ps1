[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$OutputDirectory = "backups"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$absoluteOutput = Join-Path $ProjectRoot $OutputDirectory
New-Item -ItemType Directory -Path $absoluteOutput -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputPath = Join-Path $absoluteOutput "yoru-$timestamp.sql"

Push-Location $ProjectRoot
try {
    docker compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' |
        Set-Content -LiteralPath $outputPath -Encoding UTF8
} finally {
    Pop-Location
}

if ((Get-Item -LiteralPath $outputPath).Length -le 0) {
    throw "Backup file is empty: $outputPath"
}
$hash = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Backup created: $outputPath"
Write-Host "SHA256: $hash"
