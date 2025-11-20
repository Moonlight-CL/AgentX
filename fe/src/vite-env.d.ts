/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AZURE_CLIENT_ID?: string
  readonly VITE_AZURE_TENANT_ID?: string
  readonly VITE_AZURE_AUTHORITY?: string
  readonly VITE_AZURE_REDIRECT_URI?: string
  readonly VITE_AZURE_POST_LOGOUT_REDIRECT_URI?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Runtime environment variables injected by Docker
interface Window {
  _env_?: {
    VITE_AZURE_CLIENT_ID?: string
    VITE_AZURE_TENANT_ID?: string
    VITE_AZURE_AUTHORITY?: string
    VITE_AZURE_REDIRECT_URI?: string
    VITE_AZURE_POST_LOGOUT_REDIRECT_URI?: string
  }
}

