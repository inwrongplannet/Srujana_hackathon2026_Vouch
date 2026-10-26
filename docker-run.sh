#!/usr/bin/env bash
# VeriTrust Docker Launcher Script
# Launches the backend and then the frontend, forwarding ports so they can be accessed.

set -e

echo "=========================================================="
echo " VeriTrust Docker Launcher"
echo "=========================================================="

# 1. Check if Docker CLI is installed
if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker CLI is not installed or not in PATH."
  echo "Please install Docker from https://www.docker.com/"
  exit 1
fi

# 2. Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running."
  echo "Please start Docker Desktop and run this script again."
  exit 1
fi

echo "Docker daemon detected."
echo "Building and launching VeriTrust services with Docker Compose..."
echo "  - Backend API:    http://localhost:8000 (OpenAPI /docs)"
echo "  - Frontend UI:    http://localhost:5173"
echo "----------------------------------------------------------"
echo "Press Ctrl+C to stop the containers."
echo "----------------------------------------------------------"

# Launch backend and frontend with docker compose
docker compose up --build
