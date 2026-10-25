import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ mode }) => {
  // VITE_API_BASE_URL picks the backend the dev proxy forwards to (a teammate's machine, say).
  const api = process.env.VITE_API_BASE_URL || loadEnv(mode, '..', 'VITE_').VITE_API_BASE_URL || 'http://localhost:8000';
  return {
    plugins: [react(), tailwindcss()],
    // The repo-root .env.example is the single place env keys are documented.
    envDir: '..',
    // Dev only: the browser calls /api and /health on :5173 and Vite forwards them to the FastAPI
    // backend, so the page never needs the backend's host or CORS.
    server: {
      allowedHosts: true,
      proxy: {
        '/api': { target: api, changeOrigin: true },
        '/health': { target: api, changeOrigin: true },
      },
    },
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
  };
});
