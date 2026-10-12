import { login, logout, isAuthenticated, getCurrentUser, handleCallbackIfPresent } from './lib/auth.js';
import { callApi } from './lib/api.js';

const ENDPOINTS = [
  { label: 'Public info', path: '/api/public', note: 'No login required' },
  { label: 'My profile', path: '/api/me', note: 'Any logged-in user' },
  { label: 'Dashboard', path: '/api/dashboard', note: 'Any logged-in user (content varies by role)' },
  { label: 'Reports summary', path: '/api/reports/summary', note: 'Any logged-in user' },
  { label: 'Departments (lookup)', path: '/api/lookup/departments', note: 'admin, manager only' },
  { label: 'Statuses (lookup)', path: '/api/lookup/statuses', note: 'admin, manager only' },
  { label: 'Reports (raw)', path: '/api/reports', note: 'admin, manager only' },
  { label: 'All users', path: '/api/users', note: 'admin only' },
];

const app = document.getElementById('app');

async function main() {
  try {
    await handleCallbackIfPresent();
  } catch (err) {
    renderError(err.message);
    return;
  }

  if (!isAuthenticated()) {
    renderLoggedOut();
    return;
  }

  renderLoggedIn();
}

function renderError(message) {
  app.innerHTML = `
    <div class="card error">
      <h2>Login error</h2>
      <p>${message}</p>
      <button id="retry">Back to login</button>
    </div>
  `;
  document.getElementById('retry').onclick = () => window.location.assign('/');
}

function renderLoggedOut() {
  app.innerHTML = `
    <div class="card">
      <h1>RBAC Demo</h1>
      <p>FastAPI backend + Vite frontend, secured with Keycloak (OAuth2 / OIDC, Authorization Code + PKCE).</p>
      <button id="login">Log in</button>
      <p class="hint">Demo users: <code>alice/admin123</code> (admin), <code>bob/manager123</code> (manager), <code>carol/user123</code> (user)</p>
    </div>
  `;
  document.getElementById('login').onclick = login;
}

function renderLoggedIn() {
  const user = getCurrentUser();
  app.innerHTML = `
    <div class="card">
      <div class="header-row">
        <div>
          <h1>RBAC Demo</h1>
          <p>Logged in as <strong>${user.username}</strong> &middot; role(s): <span class="roles">${user.roles.join(', ') || 'none'}</span></p>
        </div>
        <button id="logout">Log out</button>
      </div>
      <h2>Try the endpoints</h2>
      <p class="hint">Each button calls the FastAPI backend with your access token. Endpoints your role can't access will return 403.</p>
      <div id="endpoints" class="endpoint-grid"></div>
      <h2>Result</h2>
      <pre id="result">Click an endpoint above to see the response...</pre>
    </div>
  `;

  document.getElementById('logout').onclick = logout;

  const grid = document.getElementById('endpoints');
  ENDPOINTS.forEach((ep) => {
    const btn = document.createElement('button');
    btn.className = 'endpoint-btn';
    btn.innerHTML = `${ep.label}<span class="note">${ep.note}</span>`;
    btn.onclick = () => runEndpoint(ep, btn);
    grid.appendChild(btn);
  });
}

async function runEndpoint(ep, btn) {
  const result = document.getElementById('result');
  result.textContent = 'Loading...';
  document.querySelectorAll('.endpoint-btn').forEach((b) => b.classList.remove('active'));
  btn.classList.add('active');

  const { ok, status, data } = await callApi(ep.path);
  result.innerHTML = `<span class="status ${ok ? 'ok' : 'fail'}">HTTP ${status}</span>\n${JSON.stringify(data, null, 2)}`;
}

main();
