"""
Idempotent Keycloak provisioning script.

Uses only the Python standard library (no pip install needed) to talk to
the Keycloak Admin REST API and create:
  - a realm called `rbac-demo`
  - three realm roles: admin, manager, user
  - a public SPA client (`rbac-demo-app`) with PKCE enabled
  - an audience mapper so access tokens carry `aud=rbac-demo-app`
  - three demo users, one per role

Safe to run multiple times: every step first checks whether the object
already exists before creating it.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
ADMIN_USER = os.environ.get("KC_ADMIN", "admin")
ADMIN_PASS = os.environ.get("KC_ADMIN_PASSWORD", "admin")
REALM = os.environ.get("KC_REALM", "rbac-demo")
CLIENT_ID = os.environ.get("KC_CLIENT_ID", "rbac-demo-app")
FRONTEND_ORIGIN = os.environ.get("KC_FRONTEND_ORIGIN", "http://localhost:5173")

DEMO_USERS = [
    # username, password, first name, last name, role
    ("alice", "admin123", "Alice", "Admin", "admin"),
    ("bob", "manager123", "Bob", "Manager", "manager"),
    ("carol", "user123", "Carol", "User", "user"),
]


def request(method, path, token=None, body=None):
    url = f"{KEYCLOAK_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="ignore")


def wait_for_keycloak():
    print("Waiting for Keycloak to be ready...")
    for _ in range(80):
        try:
            status, _ = request("GET", "/realms/master/.well-known/openid-configuration")
            if status == 200:
                print("Keycloak is up.")
                return
        except Exception:
            pass
        time.sleep(3)
    print("Keycloak did not become ready in time.")
    sys.exit(1)


def get_admin_token():
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    data = urllib.parse.urlencode(
        {
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
            "grant_type": "password",
        }
    ).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def ensure_realm(token):
    status, _ = request("GET", f"/admin/realms/{REALM}", token=token)
    if status == 200:
        print(f"Realm '{REALM}' already exists, skipping.")
        return
    print(f"Creating realm '{REALM}'...")
    status, resp = request(
        "POST",
        "/admin/realms",
        token=token,
        body={"realm": REALM, "enabled": True, "sslRequired": "none"},
    )
    if status not in (201, 204):
        print("Failed to create realm:", status, resp)
        sys.exit(1)


def ensure_roles(token):
    for role in ("admin", "manager", "user"):
        status, _ = request("GET", f"/admin/realms/{REALM}/roles/{role}", token=token)
        if status == 200:
            continue
        print(f"Creating role '{role}'...")
        request("POST", f"/admin/realms/{REALM}/roles", token=token, body={"name": role})


def ensure_client(token):
    status, existing = request(
        "GET", f"/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", token=token
    )
    if status == 200 and existing:
        print(f"Client '{CLIENT_ID}' already exists, skipping.")
        return existing[0]["id"]

    print(f"Creating client '{CLIENT_ID}'...")
    status, resp = request(
        "POST",
        f"/admin/realms/{REALM}/clients",
        token=token,
        body={
            "clientId": CLIENT_ID,
            "publicClient": True,
            "protocol": "openid-connect",
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "redirectUris": [f"{FRONTEND_ORIGIN}/*"],
            "webOrigins": [FRONTEND_ORIGIN],
            "attributes": {
                "pkce.code.challenge.method": "S256",
                "post.logout.redirect.uris": f"{FRONTEND_ORIGIN}/*",
            },
        },
    )
    if status not in (201, 204):
        print("Failed to create client:", status, resp)
        sys.exit(1)
    _, clients = request(
        "GET", f"/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", token=token
    )
    return clients[0]["id"]


def ensure_audience_mapper(token, client_uuid):
    status, mappers = request(
        "GET",
        f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        token=token,
    )
    if any(m["name"] == "audience-mapper" for m in (mappers or [])):
        return
    print("Adding audience mapper (aud=%s)..." % CLIENT_ID)
    request(
        "POST",
        f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        token=token,
        body={
            "name": "audience-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "config": {
                "included.client.audience": CLIENT_ID,
                "id.token.claim": "false",
                "access.token.claim": "true",
            },
        },
    )


def ensure_user(token, username, password, first, last, role):
    status, existing = request(
        "GET", f"/admin/realms/{REALM}/users?username={username}", token=token
    )
    if status == 200 and existing:
        user_id = existing[0]["id"]
        print(f"User '{username}' already exists, skipping creation.")
    else:
        print(f"Creating user '{username}' ({role})...")
        status, _ = request(
            "POST",
            f"/admin/realms/{REALM}/users",
            token=token,
            body={
                "username": username,
                "email": f"{username}@example.com",
                "emailVerified": True,
                "enabled": True,
                "firstName": first,
                "lastName": last,
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            },
        )
        if status not in (201, 204):
            print("Failed to create user:", status)
            return
        _, existing = request(
            "GET", f"/admin/realms/{REALM}/users?username={username}", token=token
        )
        user_id = existing[0]["id"]

    _, role_repr = request("GET", f"/admin/realms/{REALM}/roles/{role}", token=token)
    request(
        "POST",
        f"/admin/realms/{REALM}/users/{user_id}/role-mappings/realm",
        token=token,
        body=[role_repr],
    )


def main():
    wait_for_keycloak()
    token = get_admin_token()
    ensure_realm(token)
    ensure_roles(token)
    client_uuid = ensure_client(token)
    ensure_audience_mapper(token, client_uuid)
    for username, password, first, last, role in DEMO_USERS:
        ensure_user(token, username, password, first, last, role)
    print("\nKeycloak realm setup complete.")
    print(f"Issuer:    {KEYCLOAK_URL}/realms/{REALM}")
    print(f"Client ID: {CLIENT_ID}")
    print("Demo users: alice/admin123 (admin), bob/manager123 (manager), carol/user123 (user)")


if __name__ == "__main__":
    main()
