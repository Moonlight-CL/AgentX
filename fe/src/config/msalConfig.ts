import type { Configuration, PopupRequest } from '@azure/msal-browser';

// Get environment variables from runtime config or build-time env
const getEnvVar = (key: string): string => {
  // @ts-ignore - window._env_ is injected at runtime
  return window._env_?.[key] || import.meta.env[key] || '';
};

// MSAL configuration
export const msalConfig: Configuration = {
  auth: {
    clientId: getEnvVar('VITE_AZURE_CLIENT_ID') || 'your-client-id',
    authority: getEnvVar('VITE_AZURE_AUTHORITY') || 'https://login.microsoftonline.com/your-tenant-id',
    redirectUri: getEnvVar('VITE_AZURE_REDIRECT_URI') || window.location.origin,
    postLogoutRedirectUri: getEnvVar('VITE_AZURE_POST_LOGOUT_REDIRECT_URI') || window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage', // This configures where your cache will be stored
    storeAuthStateInCookie: false, // Set this to "true" if you are having issues on IE11 or Edge
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case 0: // LogLevel.Error
            console.error(message);
            return;
          case 1: // LogLevel.Warning
            console.warn(message);
            return;
          case 2: // LogLevel.Info
            console.info(message);
            return;
          case 3: // LogLevel.Verbose
            console.debug(message);
            return;
        }
      },
    },
  },
};

// Add scopes here for ID token to be used at Microsoft identity platform endpoints.
export const loginRequest: PopupRequest = {
  scopes: ['User.Read', 'openid', 'profile', 'email'],
  prompt: 'select_account',
};

// Add the endpoints here for Microsoft Graph API services you'd like to use.
export const graphConfig = {
  graphMeEndpoint: 'https://graph.microsoft.com/v1.0/me',
  graphMePhotoEndpoint: 'https://graph.microsoft.com/v1.0/me/photo/$value',
};

// Scopes for accessing Microsoft Graph
export const graphScopes = {
  userRead: ['User.Read'],
  userReadAll: ['User.ReadBasic.All'],
  groupReadAll: ['Group.Read.All'],
};

// Environment variables validation
export const validateMsalConfig = (): boolean => {
  const requiredEnvVars = [
    'VITE_AZURE_CLIENT_ID',
    'VITE_AZURE_AUTHORITY',
  ];

  const missingVars = requiredEnvVars.filter(
    (varName) => !getEnvVar(varName)
  );

  if (missingVars.length > 0) {
    console.warn(
      `Missing Azure AD environment variables: ${missingVars.join(', ')}`
    );
    return false;
  }

  return true;
};

// Check if Azure AD is properly configured
export const isAzureAdConfigured = (): boolean => {
  return validateMsalConfig() && 
         msalConfig.auth.clientId !== 'your-client-id' &&
         !msalConfig.auth.authority?.includes('your-tenant-id');
};
