param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

docker compose up -d postgres redis qdrant
Write-Host "Infrastructure started."
Write-Host "Run these commands in separate terminals:"
Write-Host "  pnpm dev"
Write-Host "  .\.venv\Scripts\uvicorn.exe yoru_api.main:app --app-dir services/api/src --reload --port 8000"
Write-Host "  .\.venv\Scripts\python.exe -m yoru_worker.main"
