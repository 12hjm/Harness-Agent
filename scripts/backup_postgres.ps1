param(
    [string]$OutputDir = "data/backups"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force $OutputDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$file = "$OutputDir/rag-$timestamp.sql"

docker compose exec -T postgres pg_dump -U rag -d rag | Out-File -Encoding utf8 $file
Write-Host "Backup written to $file"

