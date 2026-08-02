[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$live = Invoke-RestMethod -Uri "$BaseUrl/health/live" -Method Get
$ready = Invoke-RestMethod -Uri "$BaseUrl/health/ready" -Method Get
$root = Invoke-RestMethod -Uri "$BaseUrl/" -Method Get

if ($root.version -ne "1.0.0") {
    throw "Expected API version 1.0.0, found $($root.version)"
}

Write-Host "Live check:  OK"
Write-Host "Ready check: OK"
Write-Host "API version: $($root.version)"
