import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'
import { msalConfig, isAzureAdConfigured } from './config/msalConfig'
import './index.css'
import './styles/file-download.css'
import App from './App.tsx'

const azureAdEnabled = isAzureAdConfigured()
const msalInstance = azureAdEnabled ? new PublicClientApplication(msalConfig) : null

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {azureAdEnabled && msalInstance ? (
      <MsalProvider instance={msalInstance}>
        <App />
      </MsalProvider>
    ) : (
      <App />
    )}
  </StrictMode>,
)
