param(
    [Parameter(Mandatory = $true)]
    [string]$Email,

    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$apiContainer = docker compose ps --status running --quiet api
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($apiContainer)) {
    throw "Yoru API container is not running."
}

docker compose exec api yoru-bootstrap-admin --email $Email --name $Name
if ($LASTEXITCODE -ne 0) {
    throw "Super admin bootstrap failed."
}
