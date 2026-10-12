import { createPkcePair, randomState } from './pkce.js';

const ISSUER = import.meta.env.VITE_KEYCLOAK_ISSUER;
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID;
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI;

const AUTHORIZE_ENDPOINT = `${ISSUER}/protocol/openid-connect/auth`;
const TOKEN_ENDPOINT = `${ISSUER}/protocol/openid-connect/token`;
const LOGOUT_ENDPOINT = `${ISSUER}/protocol/openid-connect/logout`;

const STORAGE = {
  verifier: 'rbac_demo_pkce_verifier',
  state: 'rbac_demo_oauth_state',
  accessToken: 'rbac_demo_access_token',
  refreshToken: 'rbac_demo_refresh_token',
  idToken: 'rbac_demo_id_token',
};

/** Redirect the browser to Keycloak's login page (Authorization Code + PKCE). */
export async function login() {
  const { verifier, challenge } = await createPkcePair();
  const state = randomState();
  sessionStorage.setItem(STORAGE.verifier, verifier);
  sessionStorage.setItem(STORAGE.state, state);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email',
    code_challenge: challenge,
    code_challenge_method: 'S256',
    state,
  });

  window.location.href = `${AUTHORIZE_ENDPOINT}?${params.toString()}`;
}

/** Log out locally and end the session at Keycloak. */
export function logout() {
  sessionStorage.removeItem(STORAGE.accessToken);
  sessionStorage.removeItem(STORAGE.refreshToken);
  sessionStorage.removeItem(STORAGE.idToken);
  const idToken = sessionStorage.getItem(STORAGE.idToken);
  const params = new URLSearchParams({ post_logout_redirect_uri: REDIRECT_URI });
  if (idToken) params.set('id_token_hint', idToken);
  window.location.href = `${LOGOUT_ENDPOINT}?${params.toString()}`;
}

/** If the current URL has ?code=..., exchange it for tokens. Returns true if handled. */
export async function handleCallbackIfPresent() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const state = params.get('state');
  if (!code) return false;

  const expectedState = sessionStorage.getItem(STORAGE.state);
  if (!expectedState || state !== expectedState) {
    throw new Error('OAuth state mismatch -- possible CSRF, aborting.');
  }
  const verifier = sessionStorage.getItem(STORAGE.verifier);

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: CLIENT_ID,
    code,
    redirect_uri: REDIRECT_URI,
    code_verifier: verifier,
  });

  const resp = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!resp.ok) {
    throw new Error(`Token exchange failed: ${resp.status} ${await resp.text()}`);
  }

  const tokens = await resp.json();
  sessionStorage.setItem(STORAGE.accessToken, tokens.access_token);
  if (tokens.refresh_token) sessionStorage.setItem(STORAGE.refreshToken, tokens.refresh_token);
  if (tokens.id_token) sessionStorage.setItem(STORAGE.idToken, tokens.id_token);

  sessionStorage.removeItem(STORAGE.verifier);
  sessionStorage.removeItem(STORAGE.state);

  // Clean the ?code&state out of the address bar.
  window.history.replaceState({}, document.title, REDIRECT_URI);
  return true;
}

export function getAccessToken() {
  return sessionStorage.getItem(STORAGE.accessToken);
}

export function isAuthenticated() {
  const token = getAccessToken();
  if (!token) return false;
  const payload = decodeJwt(token);
  if (!payload?.exp) return false;
  return payload.exp * 1000 > Date.now();
}

/** Decode a JWT payload client-side for display/UX only -- never trust this for security. */
export function decodeJwt(token) {
  try {
    const payload = token.split('.')[1];
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function getCurrentUser() {
  const token = getAccessToken();
  if (!token) return null;
  const payload = decodeJwt(token);
  if (!payload) return null;
  return {
    username: payload.preferred_username,
    email: payload.email,
    roles:
      payload.realm_access?.roles?.filter(
        (r) => !r.startsWith('default-') && !['offline_access', 'uma_authorization'].includes(r)
      ) ?? [],
  };
}

export function hasRole(...roles) {
  const user = getCurrentUser();
  if (!user) return false;
  return roles.some((r) => user.roles.includes(r));
}
