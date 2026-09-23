# crud/user.py
from logger import log
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from models.user import User, UserRole
from models.prediction import Prediction
from schemas.user import CreateUserRequest, UpdateUserRequest
from exceptions import NotFoundError, ConflictError

async def get_user_by_id(db: AsyncSession, user_id: int):
    """Fetch a single user by PK — raises NotFoundError if missing."""
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found", user_id=user_id)
    return user

async def get_user_by_email(db: AsyncSession, email: str):
    """Return the user with this email, or None."""
    stmt   = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
):
    """Return a page of users and the total count — two queries."""
    page_stmt  = select(User).order_by(User.id).offset(skip).limit(limit)
    page_result = await db.execute(page_stmt)
    users = list(page_result.scalars().all())

    count_stmt   = select(func.count()).select_from(User)
    count_result = await db.execute(count_stmt)
    total        = count_result.scalar_one()

    return users, total

async def create_user(db: AsyncSession, body: CreateUserRequest):
    """Create a new user — raises ConflictError on duplicate email."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        log.warning("create_user_duplicate_email", email=body.email)
        raise ConflictError("Email already registered", email=body.email)

    user = User(
        name             = body.name,
        email            = body.email,
        hashed_password  = f"hashed:{body.password}", 
        age              = body.age,
        role             = UserRole(body.role.value),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    log.info("user_created", user_id=user.id, email=user.email, role=user.role.value)
    
    return user

async def update_user(
    db: AsyncSession,
    user_id: int,
    body: UpdateUserRequest,
):
    """Update name and/or age on an existing user."""
    user = await get_user_by_id(db, user_id)

    if body.name is not None:
        user.name = body.name
    if body.age is not None:
        user.age = body.age

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int):
    """Hard-delete a user row."""
    user = await get_user_by_id(db, user_id)
    await db.delete(user)
    await db.commit()

async def get_user_with_predictions(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
):
    """
    Fetch a user and a page of their most recent predictions.
    Uses selectinload to avoid N+1 — 2 queries total.
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.predictions)
        )
        .where(User.id == user_id)
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    user   = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User {user_id} not found", user_id=user_id)
    return user

async def get_users_with_prediction_counts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
):
    """
    Return users paired with their prediction count —
    single query using a subquery, no loading the full predictions.
    """
    count_sub = (
        select(
            Prediction.user_id,
            func.count(Prediction.id).label("pred_count"),
        )
        .group_by(Prediction.user_id)
        .subquery()
    )

    stmt = (
        select(User, func.coalesce(count_sub.c.pred_count, 0).label("pred_count"))
        .outerjoin(count_sub, User.id == count_sub.c.user_id)
        .order_by(User.id)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    return list(result.all())