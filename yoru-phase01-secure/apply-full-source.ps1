[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    $parent = Split-Path -Parent $FilePath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

$packageRoot = $PSScriptRoot
$payloadRoot = Join-Path $packageRoot "payload"
$manifestPath = Join-Path $packageRoot "manifest.sha256"

if (-not (Test-Path -LiteralPath $payloadRoot -PathType Container)) {
    throw "Payload tidak ditemukan: $payloadRoot"
}

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifest tidak ditemukan: $manifestPath"
}

$requiredPayloadFiles = @(
    "docker-compose.yml",
    "package.json",
    ".yoru-release.json",
    "services\api\alembic\versions\20260728_0002_identity_authorization.py"
)

foreach ($requiredFile in $requiredPayloadFiles) {
    $requiredPath = Join-Path $payloadRoot $requiredFile
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Payload tidak lengkap. File wajib tidak ditemukan: $requiredFile"
    }
}

$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
$filesystemRoot = [System.IO.Path]::GetPathRoot($projectRootFull)
$trimChars = [char[]]@(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
)

if (
    $projectRootFull.TrimEnd($trimChars) -eq
    $filesystemRoot.TrimEnd($trimChars)
) {
    throw "ProjectRoot tidak boleh menunjuk langsung ke root drive."
}

if (-not (Test-Path -LiteralPath $projectRootFull)) {
    New-Item -ItemType Directory -Path $projectRootFull -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $projectRootFull -PathType Container)) {
    throw "ProjectRoot bukan sebuah folder: $projectRootFull"
}

$payloadRootFull = (Resolve-Path -LiteralPath $payloadRoot).Path
$manifestLines = Get-Content -LiteralPath $manifestPath
$manifestEntries = @()

foreach ($line in $manifestLines) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    if ($line -notmatch "^([0-9a-fA-F]{64})  (.+)$") {
        throw "Format manifest tidak valid: $line"
    }

    $expectedHash = $Matches[1].ToLowerInvariant()
    $relativePath = $Matches[2]

    if ([System.IO.Path]::IsPathRooted($relativePath)) {
        throw "Manifest memiliki absolute path yang tidak diizinkan: $relativePath"
    }

    $normalizedRelativePath = $relativePath.Replace(
        "/",
        [System.IO.Path]::DirectorySeparatorChar
    )
    $pathParts = $normalizedRelativePath.Split(
        [System.IO.Path]::DirectorySeparatorChar
    )

    if ($pathParts -contains "..") {
        throw "Manifest memiliki path traversal yang tidak diizinkan: $relativePath"
    }

    if ($normalizedRelativePath -eq ".env") {
        throw "Payload tidak boleh berisi file .env."
    }

    $sourcePath = [System.IO.Path]::GetFullPath(
        (Join-Path $payloadRootFull $normalizedRelativePath)
    )
    $destinationPath = [System.IO.Path]::GetFullPath(
        (Join-Path $projectRootFull $normalizedRelativePath)
    )

    $payloadBoundary = $payloadRootFull.TrimEnd($trimChars) +
        [System.IO.Path]::DirectorySeparatorChar
    $projectBoundary = $projectRootFull.TrimEnd($trimChars) +
        [System.IO.Path]::DirectorySeparatorChar

    if (-not $sourcePath.StartsWith(
        $payloadBoundary,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Source keluar dari payload: $relativePath"
    }

    if (-not $destinationPath.StartsWith(
        $projectBoundary,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Destination keluar dari ProjectRoot: $relativePath"
    }

    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "File pada manifest tidak ditemukan: $relativePath"
    }

    $manifestEntries += [PSCustomObject]@{
        RelativePath = $normalizedRelativePath
        SourcePath = $sourcePath
        DestinationPath = $destinationPath
        ExpectedHash = $expectedHash
    }
}

if ($manifestEntries.Count -eq 0) {
    throw "Manifest tidak berisi file."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $projectRootFull ".yoru-backups\phase01-$timestamp"
$createdFiles = [System.Collections.Generic.List[string]]::new()
$backups = @()

Write-Host ""
Write-Host "Yoru Phase 0+1 Full Source Installer" -ForegroundColor Cyan
Write-Host "Package root : $packageRoot"
Write-Host "Project root : $projectRootFull"
Write-Host "File count   : $($manifestEntries.Count)"
Write-Host ""

try {
    foreach ($entry in $manifestEntries) {
        if (Test-Path -LiteralPath $entry.DestinationPath -PathType Container) {
            throw "Destination seharusnya file tetapi berupa folder: $($entry.RelativePath)"
        }

        if (Test-Path -LiteralPath $entry.DestinationPath -PathType Leaf) {
            $backupPath = Join-Path $backupRoot $entry.RelativePath
            New-ParentDirectory -FilePath $backupPath
            Copy-Item -LiteralPath $entry.DestinationPath -Destination $backupPath -Force
            $backups += [PSCustomObject]@{
                BackupPath = $backupPath
                DestinationPath = $entry.DestinationPath
            }
        }
        else {
            $createdFiles.Add($entry.DestinationPath)
        }
    }

    foreach ($entry in $manifestEntries) {
        New-ParentDirectory -FilePath $entry.DestinationPath
        Copy-Item -LiteralPath $entry.SourcePath -Destination $entry.DestinationPath -Force
    }

    foreach ($entry in $manifestEntries) {
        $actualHash = (
            Get-FileHash -LiteralPath $entry.DestinationPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()

        if ($actualHash -ne $entry.ExpectedHash) {
            throw "Checksum tidak cocok setelah copy: $($entry.RelativePath)"
        }
    }

    $releasePath = Join-Path $projectRootFull ".yoru-release.json"
    $release = Get-Content -LiteralPath $releasePath -Raw | ConvertFrom-Json

    if ($release.version -ne "0.2.1" -or $release.release -ne "phase-01") {
        throw "Release marker hasil instalasi tidak sesuai."
    }

    $migrationPath = Join-Path $projectRootFull (
        "services\api\alembic\versions\" +
        "20260728_0002_identity_authorization.py"
    )
    $migrationSource = Get-Content -LiteralPath $migrationPath -Raw

    if ($migrationSource -notmatch "def _role_seed_statement") {
        throw "Hotfix UUID migration tidak ditemukan setelah instalasi."
    }
}
catch {
    Write-Host ""
    Write-Host "Instalasi gagal. Mengembalikan file yang sudah ditimpa..." -ForegroundColor Red

    foreach ($createdFile in $createdFiles) {
        if (Test-Path -LiteralPath $createdFile -PathType Leaf) {
            Remove-Item -LiteralPath $createdFile -Force
        }
    }

    foreach ($backup in $backups) {
        New-ParentDirectory -FilePath $backup.DestinationPath
        Copy-Item `
            -LiteralPath $backup.BackupPath `
            -Destination $backup.DestinationPath `
            -Force
    }

    throw
}

Write-Host ""
Write-Host "Phase 0+1 berhasil diterapkan." -ForegroundColor Green
Write-Host "Versi       : 0.2.1"
Write-Host "Alembic head: 20260728_0002"

if (Test-Path -LiteralPath $backupRoot -PathType Container) {
    Write-Host "Backup      : $backupRoot"
}

Write-Host ""
Write-Host "Langkah berikutnya:" -ForegroundColor Yellow
Write-Host "  cd `"$projectRootFull`""
Write-Host "  docker compose down"
Write-Host "  docker compose build --no-cache migrate api worker"
Write-Host "  docker compose run --rm migrate"
Write-Host "  docker compose up -d --build"
Write-Host "  docker compose ps"
