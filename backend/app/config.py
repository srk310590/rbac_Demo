import os

from dotenv import load_dotenv

load_dotenv()

# Issuer = the realm's base URL. Keycloak exposes discovery info at
# {KEYCLOAK_ISSUER}/.well-known/openid-configuration
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/rbac-demo")

# Must match the audience (client ID) baked into the access token via the
# audience mapper configured in keycloak/setup_realm.py
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "rbac-demo-app")

JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
