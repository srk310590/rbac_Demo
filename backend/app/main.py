from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import verify_token
from .config import CORS_ORIGINS
from .data import APP_USERS, DEPARTMENTS, REPORTS, STATUSES
from .rbac import require_roles

app = FastAPI(title="RBAC Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Public -- no token required
# ---------------------------------------------------------------------------
@app.get("/api/public")
def public_info():
    return {
        "message": "This endpoint is public. No login required.",
        "app": "rbac-demo",
    }


# ---------------------------------------------------------------------------
# Any authenticated user (admin, manager, or user)
# ---------------------------------------------------------------------------
@app.get("/api/me")
def read_me(current_user: dict = Depends(verify_token)):
    return {
        "sub": current_user["sub"],
        "username": current_user["username"],
        "email": current_user["email"],
        "roles": current_user["roles"],
    }


@app.get("/api/dashboard")
def dashboard(current_user: dict = Depends(verify_token)):
    """Everyone gets a dashboard, but the payload is tailored to their role."""
    base = {
        "welcome": f"Hello, {current_user['username']}",
        "open_reports": sum(1 for r in REPORTS if r["status_id"] == 1),
        "total_reports": len(REPORTS),
    }
    if "admin" in current_user["roles"] or "manager" in current_user["roles"]:
        base["total_users"] = len(APP_USERS)
        base["departments"] = len(DEPARTMENTS)
    return base


@app.get("/api/reports/summary")
def reports_summary(current_user: dict = Depends(verify_token)):
    """Safe, aggregated view available to every role -- no raw row data."""
    return {
        "total_reports": len(REPORTS),
        "by_status": {
            s["label"]: sum(1 for r in REPORTS if r["status_id"] == s["id"]) for s in STATUSES
        },
    }


# ---------------------------------------------------------------------------
# Admin + manager only -- raw lookup tables and full report rows
# ---------------------------------------------------------------------------
@app.get("/api/lookup/departments")
def lookup_departments(current_user: dict = Depends(require_roles("admin", "manager"))):
    return DEPARTMENTS


@app.get("/api/lookup/statuses")
def lookup_statuses(current_user: dict = Depends(require_roles("admin", "manager"))):
    return STATUSES


@app.get("/api/reports")
def list_reports(current_user: dict = Depends(require_roles("admin", "manager"))):
    return REPORTS


@app.get("/api/reports/{report_id}")
def get_report(report_id: int, current_user: dict = Depends(require_roles("admin", "manager"))):
    report = next((r for r in REPORTS if r["id"] == report_id), None)
    if report is None:
        return {"error": "not found"}
    return report


# ---------------------------------------------------------------------------
# Admin only -- most sensitive: the list of application users and their roles
# ---------------------------------------------------------------------------
@app.get("/api/users")
def list_users(current_user: dict = Depends(require_roles("admin"))):
    return APP_USERS
