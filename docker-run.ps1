# VeriTrust Docker Launcher Script (PowerShell)
# Launches the backend and then the frontend, forwarding ports so they can be accessed.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " VeriTrust Docker Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if Docker CLI is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker CLI is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/" -ForegroundColor Yellow
    exit 1
}

# 2. Check if Docker daemon is running
$dockerCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker daemon is not running." -ForegroundColor Red
    Write-Host "Please start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "Docker daemon detected." -ForegroundColor Green
Write-Host "Building and launching VeriTrust services with Docker Compose..." -ForegroundColor Green
Write-Host "  - Backend API:    http://localhost:8000 (OpenAPI /docs)" -ForegroundColor Yellow
Write-Host "  - Frontend UI:    http://localhost:5173" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"
Write-Host "Press Ctrl+C to stop the containers." -ForegroundColor Gray
Write-Host "----------------------------------------------------------"

docker compose up --build
