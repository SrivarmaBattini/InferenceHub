# dependencies/auth.py
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from exceptions import UnauthorizedError, ForbiddenError
from security import decode_access_token, is_token_revoked

from fastapi import Request

settings     = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ── Level 1: extract + decode token ───────────────────────────────────────────

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
):
    """
    Decode the JWT and return its payload.
    Does NOT hit the database — token carries id, email, role.
    Raises 401 on any token problem.
    """
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise UnauthorizedError("Token is invalid or expired") from exc

    jti = payload.get("jti")
    if jti:
        if await is_token_revoked(jti):
            raise UnauthorizedError("Token has been revoked")

    # Validate required claims exist
    if not payload.get("sub") or not payload.get("role"):
        raise UnauthorizedError("Token payload is malformed")

    return payload


# ── Level 2: add DB lookup for fresh user state ────────────────────────────────

async def get_current_active_user(
    current_user: dict[str, Any] = Depends(get_current_user),
    db:           AsyncSession   = Depends(get_db),
):
    """
    Like get_current_user but also checks the DB to confirm
    the account is still active. Use for sensitive operations
    where staleness matters (password changes, account deletion).
    """
    from crud.user import get_user_by_id
    user_id = int(current_user["sub"])
    db_user = await get_user_by_id(db, user_id)

    if not db_user.is_active:
        raise UnauthorizedError("Account has been deactivated")

    # Merge DB fields into payload for downstream use
    return {
        **current_user,
        "is_active":   db_user.is_active,
        "is_verified": db_user.is_verified,
    }


# ── Level 3: role checking ─────────────────────────────────────────────────────

def require_role(*allowed_roles: str):
    """
    Factory that returns a dependency requiring one of the given roles.

    Usage:
        Depends(require_role("admin"))
        Depends(require_role("admin", "moderator"))
    """
    async def _check_role(
        current_user: dict[str, Any] = Depends(get_current_user),
    ):
        user_role = current_user.get("role", "")
        if user_role not in allowed_roles:
            raise ForbiddenError(
                f"Required role: {' or '.join(allowed_roles)}. "
                f"Your role: {user_role}",
                required=list(allowed_roles),
                actual=user_role,
            )
        return current_user

    return _check_role


# ── Named shortcuts — import these in routers ──────────────────────────────────

require_admin = require_role("admin")
require_user  = require_role("admin", "user")   # both roles can access

async def verify_resource_owner(
    resource_user_id: int,
    current_user:     dict[str, Any] = Depends(get_current_user),
):
    """
    Pass if the current user owns the resource OR is an admin.
    Raises 403 otherwise.
    """
    is_admin = current_user.get("role") == "admin"
    is_owner = int(current_user["sub"]) == resource_user_id

    if not is_admin and not is_owner:
        raise ForbiddenError(
            "You do not have permission to modify this resource",
            resource_owner_id=resource_user_id,
            your_id=int(current_user["sub"]),
        )
    return current_user