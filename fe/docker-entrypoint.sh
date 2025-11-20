#!/bin/sh

# Create env-config.js with runtime environment variables
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  VITE_AZURE_CLIENT_ID: "${VITE_AZURE_CLIENT_ID:-}",
  VITE_AZURE_TENANT_ID: "${VITE_AZURE_TENANT_ID:-}",
  VITE_AZURE_AUTHORITY: "${VITE_AZURE_AUTHORITY:-}",
  VITE_AZURE_REDIRECT_URI: "${VITE_AZURE_REDIRECT_URI:-}",
  VITE_AZURE_POST_LOGOUT_REDIRECT_URI: "${VITE_AZURE_POST_LOGOUT_REDIRECT_URI:-}"
};
EOF

# Execute the CMD
exec "$@"
