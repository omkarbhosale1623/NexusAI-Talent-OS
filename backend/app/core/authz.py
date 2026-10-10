"""
Role-based access control (RBAC) and tenant-scoping dependencies.

The TenantMiddleware authenticates the bearer token and stashes
`request.state.org_id`, `request.state.user_id`, and `request.state.role`.
These FastAPI dependencies enforce authorization on top of that.

Usage (per-route or at include_router level):
    from app.core.authz import require_admin, require_staff, CurrentUser
    @router.post("/connections", dependencies=[Depends(require_admin)])
    ...
    async def handler(user: CurrentUser = Depends(get_current_user)): ...
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

# Role hierarchy — higher number = more privilege.
ROLE_RANK = {"viewer": 1, "recruiter": 2, "admin": 3, "owner": 4}


@dataclass
class CurrentUser:
    user_id: str
    org_id: str
    role: str


def _state(request: Request) -> tuple[Optional[str], Optional[str], str]:
    return (
        getattr(request.state, "user_id", None),
        getattr(request.state, "org_id", None),
        getattr(request.state, "role", None) or "recruiter",
    )


def get_current_user(request: Request) -> CurrentUser:
    user_id, org_id, role = _state(request)
    if not user_id or not org_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return CurrentUser(user_id=user_id, org_id=org_id, role=role)


def require_roles(*roles: str):
    """Dependency factory: allow only the given roles (or higher rank)."""
    min_rank = min((ROLE_RANK.get(r, 99) for r in roles), default=99)

    def _checker(request: Request) -> CurrentUser:
        user = get_current_user(request)
        if user.role in roles or ROLE_RANK.get(user.role, 0) >= min_rank:
            return user
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient privileges: requires one of {sorted(set(roles))}",
        )

    return _checker


# Common ready-made guards
require_admin = require_roles("admin", "owner")
require_staff = require_roles("recruiter", "admin", "owner")