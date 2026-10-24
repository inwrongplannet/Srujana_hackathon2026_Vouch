/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** ZK_STUB public demo protocol salt (see .env.example). */
  readonly VITE_DEMO_PROTOCOL_SALT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
