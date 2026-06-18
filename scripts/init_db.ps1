$ErrorActionPreference = "Stop"

docker compose up -d postgres redis qdrant
docker compose up -d api

Write-Host "Waiting for API health check..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/healthz" | Out-Null
        Write-Host "API is ready."
        exit 0
    } catch {
        Start-Sleep -Seconds 2
    }
}

throw "API did not become healthy in time."

