"""
Role-based access control.

`require_roles(...)` is a FastAPI dependency factory: pass the roles allowed
to call a given route, and it returns a dependency that first verifies the
token (via verify_token) and then checks the user's realm roles against the
allow-list. This is the actual enforcement layer -- it runs on the backend,
so it can't be bypassed by anything the frontend does or doesn't render.

Role model used in this demo (simple hierarchy, not enforced automatically --
each route just lists which roles may call it):
  - admin:   full access to everything, including raw lookup tables and the
             list of all application users
  - manager: can see reports and lookup tables, but not the user list
  - user:    can see their own profile, a dashboard, and summarized reports
             only -- no direct lookup-table or admin access
"""
from fastapi import Depends, HTTPException, status

from .auth import verify_token


def require_roles(*allowed_roles: str):
    def dependency(current_user: dict = Depends(verify_token)) -> dict:
        user_roles = set(current_user["roles"])
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Requires one of roles {sorted(allowed_roles)}, "
                    f"but user has {sorted(user_roles) or 'no'} role(s)."
                ),
            )
        return current_user

    return dependency
