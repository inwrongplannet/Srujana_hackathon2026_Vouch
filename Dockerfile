# Unified single-container Dockerfile for VeriTrust (Backend + Frontend)
FROM python:3.11-slim

WORKDIR /app

# Install Node.js 20, npm, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Install frontend dependencies
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

# Copy project files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY .env.example ./.env.example
COPY scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
RUN chmod +x ./scripts/docker-entrypoint.sh

ENV PYTHONPATH=/app/backend/src
ENV PYTHONUNBUFFERED=1
ENV VITE_API_BASE_URL=http://localhost:8000

EXPOSE 5173 8000

CMD ["./scripts/docker-entrypoint.sh"]
