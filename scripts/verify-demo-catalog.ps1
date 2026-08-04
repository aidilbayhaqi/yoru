param(
  [string]$ApiBase = "http://localhost:8000/api/v1"
)

$ErrorActionPreference = "Stop"
$products = Invoke-RestMethod "$ApiBase/catalog/products?limit=100"
$services = Invoke-RestMethod "$ApiBase/catalog/services?limit=100"

$productMedia = @($products.data | ForEach-Object { $_.media } | Where-Object { $_.status -eq "ready" })

Write-Host "Products : $(@($products.data).Count)"
Write-Host "Media    : $($productMedia.Count)"
Write-Host "Services : $(@($services.data).Count)"

if (@($products.data).Count -lt 6) { throw "Expected at least 6 products." }
if ($productMedia.Count -lt 6) { throw "Expected at least 6 ready product media rows." }
if (@($services.data).Count -lt 6) { throw "Expected at least 6 services." }

Write-Host "Demo catalog verification passed." -ForegroundColor Green
