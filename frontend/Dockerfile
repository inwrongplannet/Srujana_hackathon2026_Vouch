# Frontend Dockerfile for VeriTrust React/Vite UI
FROM node:20-alpine

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and environment configs
COPY frontend/ ./
COPY .env.example /app/.env.example

ENV VITE_API_BASE_URL=http://backend:8000
ENV HOST=0.0.0.0
ENV PORT=5173

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
