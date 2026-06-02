import {
  InteractionRequiredAuthError,
  PublicClientApplication,
} from '@azure/msal-browser'

const CLIENT_ID = import.meta.env.VITE_ENTRA_CLIENT_ID

export const apiScope = import.meta.env.VITE_ENTRA_API_SCOPE
  || (CLIENT_ID ? `api://${CLIENT_ID}/access_as_user` : undefined)

export const msalEnabled = Boolean(CLIENT_ID)

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId: CLIENT_ID || '00000000-0000-0000-0000-000000000000',
    authority: 'https://login.microsoftonline.com/common',
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage',
  },
})

export const initializeAuth = async () => {
  await msalInstance.initialize()
  const redirectResult = await msalInstance.handleRedirectPromise()
  const account = redirectResult?.account || msalInstance.getAllAccounts()[0]
  if (account) {
    msalInstance.setActiveAccount(account)
  }
}

export const loginRequest = apiScope ? { scopes: [apiScope] } : { scopes: [] }

export const getApiAccessToken = async () => {
  if (!msalEnabled) {
    return null
  }

  const account = msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0]
  if (!account) {
    return null
  }

  try {
    const result = await msalInstance.acquireTokenSilent({
      ...loginRequest,
      account,
    })
    return result.accessToken
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      return null
    }
    throw error
  }
}
