// Authorization Code + PKCE helpers. No external dependencies -- uses the
// browser's native crypto API.

function base64url(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

function randomVerifier(length = 64) {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return base64url(bytes.buffer);
}

export async function createPkcePair() {
  const verifier = randomVerifier();
  const encoded = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', encoded);
  const challenge = base64url(digest);
  return { verifier, challenge };
}

export function randomState(length = 24) {
  return randomVerifier(length);
}
