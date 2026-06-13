import React from 'react'
import ReactDOM from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import App from './App.jsx'
import { initializeAuth, msalInstance } from './auth'
import './index.css'

try {
  await initializeAuth()
} catch (error) {
  console.error(
    'Authentication initialization failed; starting without a signed-in session.',
    error,
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MsalProvider instance={msalInstance}>
      <App />
    </MsalProvider>
  </React.StrictMode>,
)
