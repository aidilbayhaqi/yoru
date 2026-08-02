[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$markerPath = Join-Path $ProjectRoot ".yoru-release.json"
if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
    throw "Release marker not found: $markerPath"
}
$release = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
if ($release.version -ne "1.0.0") {
    throw "Production preflight requires Yoru 1.0.0; found $($release.version)"
}
if ($release.alembic_head -ne "20260802_0010") {
    throw "Production preflight requires Alembic 20260802_0010; found $($release.alembic_head)"
}

Push-Location $ProjectRoot
try {
    docker compose config --quiet
    docker compose run --rm migrate alembic current
    docker compose run --rm api python -m pytest -q -o cache_dir=/tmp/pytest-cache
    docker compose run --rm api python -m pip check
    Write-Host "Production preflight completed."
    Write-Host "Still required before launch: successful restore drill, external security review, load test, and launch-gate PASS."
} finally {
    Pop-Location
}
