# routers/auth.py
from datetime import timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from schemas.auth import LoginRequest, TokenResponse
from schemas.user import CreateUserRequest, UserResponse
from security import hash_password, create_access_token
from crud.auth import authenticate_user
from crud.user import create_user, get_user_by_email
from typing import Any
from exceptions import ConflictError
from dependencies.auth import get_current_user, get_current_active_user

settings = get_settings()
router   = APIRouter(prefix="/auth", tags=["auth"])

from fastapi import BackgroundTasks
from tasks.background import send_welcome_email

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: CreateUserRequest,
    background_tasks: BackgroundTasks,
    db:   AsyncSession = Depends(get_db),
):
    """Create a new user account."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise ConflictError("Email already registered", email=body.email)

    from models.user import User, UserRole

    user = User(
        name             = body.name,
        email            = body.email,
        hashed_password  = hash_password(body.password),
        age              = body.age,
        role             = UserRole.user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(
        send_welcome_email,
        user_id = user.id,
        email   = user.email,
        name    = user.name,
    )
    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive an access token",
)
async def login(
    body: LoginRequest,
    db:   AsyncSession = Depends(get_db),
):
    """Authenticate with email + password."""
    user  = await authenticate_user(db, body)
    token = create_access_token(
        subject      = user.id,
        extra_claims = {
            "email": user.email,
            "role":  user.role.value,
        },
    )
    return TokenResponse(
        access_token = token,
        token_type   = "bearer",
        expires_in   = settings.access_token_expire_minutes * 60,
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the profile of the currently logged-in user."""
    from crud.user import get_user_by_id
    return await get_user_by_id(db, int(current_user["sub"]))

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user by revoking active JWT",
)
async def logout(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    jti = current_user.get("jti")
    exp = current_user.get("exp")
    if jti and exp:
        import time
        from security import revoke_token
        ttl = max(0, int(exp - time.time()))
        if ttl > 0:
            await revoke_token(jti, ttl)
    return {"message": "Successfully logged out"}
