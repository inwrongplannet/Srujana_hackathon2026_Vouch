/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** ZK_STUB public demo protocol salt (see .env.example). */
  readonly VITE_DEMO_PROTOCOL_SALT?: string;
  /** Backend origin the dev proxy forwards /api and /health to; default http://localhost:8000. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
