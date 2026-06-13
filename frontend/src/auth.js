import {
  EventType,
  InteractionRequiredAuthError,
  PublicClientApplication,
} from '@azure/msal-browser'

const CLIENT_ID = import.meta.env.VITE_ENTRA_CLIENT_ID
const AUTHORITY = import.meta.env.VITE_ENTRA_AUTHORITY
  || 'https://login.microsoftonline.com/common'

export const apiScope = import.meta.env.VITE_ENTRA_API_SCOPE
  || (CLIENT_ID ? `api://${CLIENT_ID}/access_as_user` : undefined)

export const msalEnabled = Boolean(CLIENT_ID)

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId: CLIENT_ID || '00000000-0000-0000-0000-000000000000',
    authority: AUTHORITY,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: 'localStorage',
  },
})

msalInstance.enableAccountStorageEvents()
msalInstance.addEventCallback((event) => {
  if (
    (event.eventType === EventType.LOGIN_SUCCESS
      || event.eventType === EventType.ACQUIRE_TOKEN_SUCCESS)
    && event.payload?.account
  ) {
    msalInstance.setActiveAccount(event.payload.account)
  }
})

export const initializeAuth = async () => {
  await msalInstance.initialize()
  const redirectResult = await msalInstance.handleRedirectPromise()
  const account = redirectResult?.account || msalInstance.getAllAccounts()[0]
  if (account) {
    msalInstance.setActiveAccount(account)
  }
}

export const loginRequest = {
  scopes: [
    'openid',
    'profile',
    'email',
    'offline_access',
    ...(apiScope ? [apiScope] : []),
  ],
}

export const logoutRequest = {
  postLogoutRedirectUri: window.location.origin,
}

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
    const reason = error instanceof InteractionRequiredAuthError
      ? 'Microsoft sign-in requires interaction'
      : 'Microsoft access token is temporarily unavailable'
    console.warn(`${reason}; continuing with anonymous demo access.`, error)
    return null
  }
}
