param(
    [string]$AdminToken = $env:ADMIN_TOKEN,
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

if (-not $AdminToken) {
    throw "Admin token is required. Pass -AdminToken or set ADMIN_TOKEN."
}

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/admin/kb/reindex" `
    -Headers @{ "X-Admin-Token" = $AdminToken } `
    -ContentType "application/json" `
    -Body '{"clear_existing":true}'

