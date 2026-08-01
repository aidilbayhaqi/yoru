[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ExpectedVersion = "0.2.1"
$TargetVersion = "0.3.0"
$TargetRelease = "phase-02"
$TargetAlembicHead = "20260731_0003"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PatchRoot "payload"
$ManifestPath = Join-Path $PatchRoot "manifest.sha256"
$RemovedFilesPath = Join-Path $PatchRoot "removed-files.txt"

function Get-SafePath {
    param(
        [string]$Root,
        [string]$RelativePath
    )

    if ([System.IO.Path]::IsPathRooted($RelativePath)) {
        throw "Absolute path is not allowed in patch: $RelativePath"
    }

    $normalizedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $candidate = [System.IO.Path]::GetFullPath((Join-Path $normalizedRoot $RelativePath))
    $prefix = $normalizedRoot + [System.IO.Path]::DirectorySeparatorChar
    if (-not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Patch path escapes project root: $RelativePath"
    }

    $blockedSegments = @(".git", ".yoru-backups")
    $segments = $RelativePath -split '[\\/]'
    foreach ($segment in $segments) {
        if ($blockedSegments -contains $segment) {
            throw "Protected path cannot be changed by patch: $RelativePath"
        }
    }
    if ($segments[-1] -eq ".env") {
        throw ".env cannot be changed by patch"
    }

    return $candidate
}

function Read-Manifest {
    param([string]$Path)

    $entries = @()
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }
        if ($trimmed -notmatch '^([0-9a-fA-F]{64})\s{2}(.+)$') {
            throw "Invalid manifest line: $line"
        }
        $entries += [PSCustomObject]@{
            Hash = $Matches[1].ToLowerInvariant()
            RelativePath = $Matches[2]
        }
    }
    return $entries
}

if (-not (Test-Path -LiteralPath $PayloadRoot -PathType Container)) {
    throw "Patch payload is missing: $PayloadRoot"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Patch manifest is missing: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Project root does not exist: $ProjectRoot"
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$ReleaseMarkerPath = Join-Path $ProjectRoot ".yoru-release.json"
if (-not (Test-Path -LiteralPath $ReleaseMarkerPath -PathType Leaf)) {
    throw "Release marker is missing: $ReleaseMarkerPath"
}

$currentRelease = Get-Content -LiteralPath $ReleaseMarkerPath -Raw | ConvertFrom-Json
if ($currentRelease.version -ne $ExpectedVersion) {
    throw "Patch requires Yoru $ExpectedVersion, found $($currentRelease.version)"
}

$manifest = Read-Manifest -Path $ManifestPath
if ($manifest.Count -eq 0) {
    throw "Manifest contains no payload files"
}

foreach ($entry in $manifest) {
    $sourcePath = Get-SafePath -Root $PayloadRoot -RelativePath $entry.RelativePath
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Manifest file is missing from payload: $($entry.RelativePath)"
    }
    $actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $entry.Hash) {
        throw "Payload checksum mismatch: $($entry.RelativePath)"
    }
}

$removedFiles = @()
if (Test-Path -LiteralPath $RemovedFilesPath -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $RemovedFilesPath) {
        $trimmed = $line.Trim()
        if (-not [string]::IsNullOrWhiteSpace($trimmed) -and -not $trimmed.StartsWith("#")) {
            $removedFiles += $trimmed
        }
    }
}

$manifestPaths = @($manifest | ForEach-Object { $_.RelativePath })
foreach ($removedFile in $removedFiles) {
    if ($manifestPaths -contains $removedFile) {
        throw "A path cannot be both copied and removed: $removedFile"
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $ProjectRoot ".yoru-backups\phase-02-partner-onboarding-$timestamp"
$BackupFilesRoot = Join-Path $BackupRoot "files"
New-Item -ItemType Directory -Path $BackupFilesRoot -Force | Out-Null
Copy-Item -LiteralPath $ReleaseMarkerPath -Destination (Join-Path $BackupRoot ".yoru-release.json")

$createdFiles = New-Object System.Collections.Generic.List[string]
$backedUpFiles = New-Object System.Collections.Generic.List[string]

try {
    foreach ($entry in $manifest) {
        $relativePath = $entry.RelativePath
        $sourcePath = Get-SafePath -Root $PayloadRoot -RelativePath $relativePath
        $destinationPath = Get-SafePath -Root $ProjectRoot -RelativePath $relativePath
        $backupPath = Get-SafePath -Root $BackupFilesRoot -RelativePath $relativePath

        if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
            Copy-Item -LiteralPath $destinationPath -Destination $backupPath -Force
            $backedUpFiles.Add($relativePath)
        } else {
            $createdFiles.Add($relativePath)
        }

        New-Item -ItemType Directory -Path (Split-Path -Parent $destinationPath) -Force | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
    }

    foreach ($relativePath in $removedFiles) {
        $destinationPath = Get-SafePath -Root $ProjectRoot -RelativePath $relativePath
        if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
            $backupPath = Get-SafePath -Root $BackupFilesRoot -RelativePath $relativePath
            New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
            Copy-Item -LiteralPath $destinationPath -Destination $backupPath -Force
            $backedUpFiles.Add($relativePath)
            Remove-Item -LiteralPath $destinationPath -Force
        }
    }

    foreach ($entry in $manifest) {
        $destinationPath = Get-SafePath -Root $ProjectRoot -RelativePath $entry.RelativePath
        $actualHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $entry.Hash) {
            throw "Installed checksum mismatch: $($entry.RelativePath)"
        }
    }

    $newRelease = [ordered]@{
        product = "Yoru Platform"
        release = $TargetRelease
        version = $TargetVersion
        includes = @(
            "phase-0-foundation",
            "phase-1-identity",
            "phase-2-partner-onboarding"
        )
        alembic_head = $TargetAlembicHead
        package_mode = "incremental-patch"
        released_at = (Get-Date).ToString("yyyy-MM-dd")
    }
    $temporaryMarker = "$ReleaseMarkerPath.tmp"
    $newRelease | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporaryMarker -Encoding UTF8
    Move-Item -LiteralPath $temporaryMarker -Destination $ReleaseMarkerPath -Force

    Write-Host "Yoru patch applied successfully: $ExpectedVersion -> $TargetVersion"
    Write-Host "Backup: $BackupRoot"
    Write-Host "Next: rebuild containers, run Alembic migration, then run tests."
} catch {
    Write-Warning "Patch failed. Restoring files from backup."

    foreach ($relativePath in $createdFiles) {
        $destinationPath = Get-SafePath -Root $ProjectRoot -RelativePath $relativePath
        if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
            Remove-Item -LiteralPath $destinationPath -Force
        }
    }

    foreach ($relativePath in $backedUpFiles) {
        $backupPath = Get-SafePath -Root $BackupFilesRoot -RelativePath $relativePath
        $destinationPath = Get-SafePath -Root $ProjectRoot -RelativePath $relativePath
        if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $destinationPath) -Force | Out-Null
            Copy-Item -LiteralPath $backupPath -Destination $destinationPath -Force
        }
    }

    $backupMarker = Join-Path $BackupRoot ".yoru-release.json"
    if (Test-Path -LiteralPath $backupMarker -PathType Leaf) {
        Copy-Item -LiteralPath $backupMarker -Destination $ReleaseMarkerPath -Force
    }

    throw
}
