# crud/auth.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.user import User
from schemas.auth import LoginRequest
from security import verify_password
from exceptions import UnauthorizedError, NotFoundError

async def authenticate_user(
    db: AsyncSession,
    credentials: LoginRequest,
):
    """Verify email + password."""
    stmt   = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user   = result.scalar_one_or_none()

    dummy_hash = "$2b$12$invalidhashforconstanttimechecks000000000000000000000"
    password_ok = verify_password(
        credentials.password,
        user.hashed_password if user else dummy_hash,
    )

    if not user or not password_ok:
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return user
