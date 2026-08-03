param(
    [string]$Email = "superadmin.demo@yoru.com",
    [string]$Name = "Yoru Demo Super Admin",
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

Write-Host "Development-only super admin bootstrap" -ForegroundColor Yellow
Write-Host "Email: $Email"
Write-Host "Password akan diminta secara aman dan tidak disimpan di source." -ForegroundColor DarkGray

$bootstrap = Join-Path $ProjectRoot "scripts\bootstrap-admin.ps1"
if (-not (Test-Path $bootstrap)) {
    throw "scripts/bootstrap-admin.ps1 tidak ditemukan."
}

& $bootstrap -Email $Email -Name $Name -ProjectRoot $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    throw "Dummy super admin bootstrap gagal."
}

Write-Host "Super admin development berhasil dibuat." -ForegroundColor Green
Write-Host "Jangan gunakan akun atau password development di production." -ForegroundColor Yellow
