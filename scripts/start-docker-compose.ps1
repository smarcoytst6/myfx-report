# start-docker-compose.ps1
Set-Location "D:\docker_myfx"

Write-Host "Waiting for Docker daemon..."
do {
    Start-Sleep -Seconds 5
    $ready = docker info 2>$null
} while (-not $ready)

docker compose up -d
Write-Host "myfx-report container started!"