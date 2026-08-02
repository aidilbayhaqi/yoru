[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$DrillDatabase = "yoru_restore_drill"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
    throw "Backup file not found: $BackupFile"
}
$BackupFile = (Resolve-Path -LiteralPath $BackupFile).Path
$started = Get-Date

Push-Location $ProjectRoot
try {
    docker compose exec -T postgres sh -lc "dropdb -U \"`$POSTGRES_USER\" --if-exists $DrillDatabase"
    docker compose exec -T postgres sh -lc "createdb -U \"`$POSTGRES_USER\" $DrillDatabase"
    Get-Content -LiteralPath $BackupFile -Raw |
        docker compose exec -T postgres sh -lc "psql -v ON_ERROR_STOP=1 -U \"`$POSTGRES_USER\" -d $DrillDatabase"
    docker compose exec -T postgres sh -lc "psql -U \"`$POSTGRES_USER\" -d $DrillDatabase -tAc 'SELECT count(*) FROM alembic_version'"
    docker compose exec -T postgres sh -lc "dropdb -U \"`$POSTGRES_USER\" --if-exists $DrillDatabase"
} finally {
    Pop-Location
}

$duration = [int]((Get-Date) - $started).TotalMilliseconds
Write-Host "Restore drill succeeded in $duration ms."
Write-Host "Record the result using POST /api/v1/platform/ops/restore-drills."
