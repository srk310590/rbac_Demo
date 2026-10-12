import { getAccessToken } from './auth.js';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Calls a backend endpoint with the current access token attached.
 * Returns { ok, status, data } instead of throwing, so the UI can render
 * 401/403 responses just like any other result.
 */
export async function callApi(path) {
  const token = getAccessToken();
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  let data;
  try {
    data = await resp.json();
  } catch {
    data = null;
  }
  return { ok: resp.ok, status: resp.status, data };
}
