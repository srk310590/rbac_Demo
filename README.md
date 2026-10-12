# RBAC Demo: FastAPI + Vite + Keycloak

A minimal monorepo showing OAuth2/OIDC authentication and role-based access
control across a Python FastAPI backend and a Vite (vanilla JS) frontend,
secured by **Keycloak** as the authorization server (free, self-hosted, runs
in Docker).

```
.
├── docker-compose.yml     # Keycloak + auto-provisioning of realm/roles/users
├── keycloak/
│   └── setup_realm.py     # Idempotent script that configures Keycloak via its Admin API
├── backend/                # FastAPI app
│   └── app/
│       ├── main.py         # Route definitions (multiple GETs, role-gated)
│       ├── auth.py         # Verifies incoming JWTs against Keycloak's JWKS
│       ├── rbac.py         # require_roles(...) dependency
│       ├── data.py         # Fake data used by the demo endpoints
│       └── config.py
└── frontend/                # Vite (vanilla JS) app
    └── src/
        ├── main.js          # UI: login button, endpoint buttons, result viewer
        ├── lib/auth.js       # PKCE login/callback/logout, token + role helpers
        ├── lib/pkce.js
        └── lib/api.js        # fetch() wrapper that attaches the bearer token
```

## How the pieces fit together

1. **Keycloak** is the authorization server. It issues access tokens (JWTs)
   after a user logs in, and embeds their roles in the token
   (`realm_access.roles`).
2. The **frontend** never handles passwords. It redirects the browser to
   Keycloak's login page (Authorization Code flow + PKCE — no client secret
   needed for a public SPA), then exchanges the returned code for tokens.
3. The **backend** never talks to Keycloak's login UI. On every request it
   validates the bearer token's signature (via Keycloak's public JWKS),
   issuer, audience and expiry, then checks the user's roles against each
   route's allow-list before returning data.

Role enforcement lives entirely in the backend (`rbac.py`). The frontend
only uses role info to decide what to *show* — never to actually protect
data, since that check can be trivially bypassed in a browser.

## RBAC matrix

| Endpoint                     | admin | manager | user | anonymous |
|-------------------------------|:-----:|:-------:|:----:|:---------:|
| `GET /api/public`             | ✅    | ✅      | ✅   | ✅        |
| `GET /api/me`                 | ✅    | ✅      | ✅   | ❌        |
| `GET /api/dashboard`          | ✅    | ✅      | ✅   | ❌        |
| `GET /api/reports/summary`    | ✅    | ✅      | ✅   | ❌        |
| `GET /api/lookup/departments` | ✅    | ✅      | ❌   | ❌        |
| `GET /api/lookup/statuses`    | ✅    | ✅      | ❌   | ❌        |
| `GET /api/reports`            | ✅    | ✅      | ❌   | ❌        |
| `GET /api/reports/{id}`       | ✅    | ✅      | ❌   | ❌        |
| `GET /api/users`              | ✅    | ❌      | ❌   | ❌        |

`user` never sees raw lookup tables or the user list directly — only a
summarized view. `manager` sees everything operational but not the sensitive
user list. `admin` sees everything.

## 1. Start Keycloak

Requires Docker.

```bash
docker compose up -d
```

This starts Keycloak and a one-shot `keycloak-setup` container that waits
for it to come up, then creates:
- realm `rbac-demo`
- realm roles `admin`, `manager`, `user`
- a public client `rbac-demo-app` (PKCE enabled, redirect URI
  `http://localhost:5173/*`)
- three demo users:

| username | password    | role    |
|----------|-------------|---------|
| alice    | admin123    | admin   |
| bob      | manager123  | manager |
| carol    | user123     | user    |

Watch the logs to confirm it finished:

```bash
docker compose logs -f keycloak-setup
```

Keycloak's admin console is at http://localhost:8080 (login: `admin` / `admin`)
if you want to poke around — inspect the realm, roles, users, or client
under **Realm settings → rbac-demo**.

## 2. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000. Docs at http://localhost:8000/docs
(note: the interactive docs won't have a login button — use the frontend, or
grab a token manually, see below).

## 3. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173, click **Log in**, sign in as one of the demo
users, and click through the endpoint buttons to see which ones succeed
(200) vs. get rejected (401/403) depending on the role.

## Getting a token manually (for curl/Postman)

Useful for testing the backend without the frontend:

```bash
curl -X POST http://localhost:8080/realms/rbac-demo/protocol/openid-connect/token \
  -d "client_id=rbac-demo-app" \
  -d "grant_type=password" \
  -d "username=alice" \
  -d "password=admin123" \
  -d "scope=openid"
```

(Direct password grant is enabled on the demo client purely for convenience
in local testing — never do this in production.) Copy the `access_token`
from the response and use it as a bearer token:

```bash
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer <access_token>"
```

## Troubleshooting

- **401 Unauthorized on every request**: check that `backend/.env`'s
  `KEYCLOAK_ISSUER` matches exactly what's in the token's `iss` claim
  (`http://localhost:8080/realms/rbac-demo`), and that the backend can
  reach Keycloak to fetch its JWKS.
- **Audience mismatch errors**: the `keycloak-setup` script adds an
  audience mapper so tokens carry `aud=rbac-demo-app`. If you rebuilt the
  realm by hand, re-check that mapper exists on the client's client scopes.
- **CORS errors in the browser console**: confirm `CORS_ORIGINS` in
  `backend/.env` includes `http://localhost:5173`.
- **Login redirect loops back to an error page**: check that the redirect
  URI in `frontend/.env` (`VITE_REDIRECT_URI`) exactly matches what's
  registered on the Keycloak client (`http://localhost:5173/*` covers it).

## Extending this demo

- Add a `require_permission("resource:action")` layer instead of role
  checks directly, if you need finer-grained access control than three
  roles.
- Swap Keycloak for Auth0/Entra/Cognito/etc — only `backend/app/config.py`
  (issuer/audience/claim path for roles) and `frontend/src/lib/auth.js`
  (endpoint URLs) need to change; the RBAC logic stays the same.
- Add a refresh-token flow in `auth.js` to silently renew access tokens
  before they expire instead of forcing re-login.
