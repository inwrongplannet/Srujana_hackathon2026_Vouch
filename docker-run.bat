@echo off
rem VeriTrust Docker Launcher Script (Windows Command Prompt)
rem Launches the backend and then the frontend, forwarding ports so they can be accessed.

echo ==========================================================
echo  VeriTrust Docker Launcher
echo ==========================================================

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker CLI is not installed or not in PATH.
    echo Please install Docker Desktop from https://www.docker.com/
    exit /b 1
)

docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker daemon is not running.
    echo Please start Docker Desktop and run this script again.
    exit /b 1
)

echo Docker daemon detected.
echo Building and launching VeriTrust services with Docker Compose...
echo   - Backend API:    http://localhost:8000 (OpenAPI /docs)
echo   - Frontend UI:    http://localhost:5173
echo ----------------------------------------------------------
echo Press Ctrl+C to stop the containers.
echo ----------------------------------------------------------

docker compose up --build
