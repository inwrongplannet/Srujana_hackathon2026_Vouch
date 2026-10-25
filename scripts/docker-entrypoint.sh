#!/bin/sh
set -e

echo "=========================================================="
echo " Starting VeriTrust Backend Service (FastAPI)..."
echo "=========================================================="
cd /app/backend
uvicorn veritrust.api.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend health check on http://localhost:8000/health..."
RETRIES=30
while [ $RETRIES -gt 0 ]; do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "[OK] Backend is healthy and ready!"
    break
  fi
  sleep 1
  RETRIES=$((RETRIES - 1))
done

if [ $RETRIES -eq 0 ]; then
  echo "[ERROR] Backend timed out starting."
  exit 1
fi

echo "=========================================================="
echo " Starting VeriTrust Frontend Service (Vite React)..."
echo "=========================================================="
cd /app/frontend
export VITE_API_BASE_URL="http://localhost:8000"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo "=========================================================="
echo " VeriTrust is running and ready for access!"
echo "   - Frontend UI:        http://localhost:5173"
echo "   - Backend API Docs:   http://localhost:8000/docs"
echo "   - Health Check:       http://localhost:8000/health"
echo "=========================================================="

wait -n $BACKEND_PID $FRONTEND_PID
