# routers/users.py
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import (
    get_current_user,
    get_current_active_user,
    require_admin,
    require_user,
    verify_resource_owner,
)
from dependencies.pagination import PaginationParams
from schemas.user import (
    CreateUserRequest, UpdateUserRequest,
    UserResponse, UserListResponse,
    UserWithPredictions,
)
from schemas.errors import error_responses
import crud.user as user_crud

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    response_model=UserListResponse,
    responses={**error_responses},
    summary="List all users — admin only",
)
async def list_users(
    pagination:  PaginationParams  = Depends(PaginationParams),
    db:          AsyncSession      = Depends(get_db),
    _admin:      dict[str, Any]    = Depends(require_admin),  # admin only
):
    users, total = await user_crud.get_users(db, pagination.skip, pagination.limit)
    return {"total": total, "users": users}


@router.get(
    "/me",
    response_model=UserResponse,
    responses={**error_responses},
    summary="Get your own profile",
)
async def get_my_profile(
    current_user: dict[str, Any] = Depends(get_current_active_user),
    db:           AsyncSession   = Depends(get_db),
):
    """Returns the authenticated user's own profile with fresh DB data."""
    user_id = int(current_user["sub"])
    return await user_crud.get_user_by_id(db, user_id)


from cache import CacheKey, cache_get, cache_set, cache_delete, cache_delete_pattern

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={**error_responses},
    summary="Get a user profile by ID",
)
async def get_user(
    user_id:      int,
    db:           AsyncSession   = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Admins can fetch any user.
    Regular users can only fetch their own profile.
    """
    await verify_resource_owner(user_id, current_user)
    
    cache_key = CacheKey.user(user_id)
    cached    = await cache_get(cache_key)
    if cached:
        print(f"[cache] HIT user key={cache_key!r}")
        return UserResponse(**cached)

    print(f"[cache] MISS user key={cache_key!r}")
    user = await user_crud.get_user_by_id(db, user_id)
    
    await cache_set(cache_key, user.model_dump() if hasattr(user, 'model_dump') else {c.name: getattr(user, c.name) for c in user.__table__.columns}, ttl=300)
    return user


from fastapi import BackgroundTasks
from tasks.background import invalidate_user_cache

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={**error_responses},
    summary="Update a user — admin or own profile",
)
async def update_user(
    user_id:      int,
    body:         UpdateUserRequest,
    background_tasks: BackgroundTasks,
    db:           AsyncSession   = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_active_user),
):
    await verify_resource_owner(user_id, current_user)
    user = await user_crud.update_user(db, user_id, body)
    
    background_tasks.add_task(cache_delete, CacheKey.user(user_id))
    background_tasks.add_task(cache_delete_pattern, f"user_predictions:{user_id}:*")
    
    return user

@router.get(
    "/{user_id}/predictions/stats",
    responses={**error_responses},
    summary="Get user's prediction statistics",
)
async def get_user_prediction_stats(
    user_id:      int,
    db:           AsyncSession   = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    await verify_resource_owner(user_id, current_user)
    from models.prediction import Prediction
    from sqlalchemy import select, func, desc
    
    # Calculate base aggregates
    stmt = select(
        func.count(Prediction.id).label("total_predictions"),
        func.coalesce(func.avg(Prediction.confidence), 0.0).label("avg_confidence"),
        func.coalesce(func.avg(Prediction.latency_ms), 0.0).label("avg_latency_ms"),
    ).where(Prediction.user_id == user_id)
    
    result = await db.execute(stmt)
    total, avg_conf, avg_lat = result.one()
    
    # Calculate mode of model_version
    mode_stmt = select(Prediction.model_version).where(Prediction.user_id == user_id).group_by(Prediction.model_version).order_by(desc(func.count(Prediction.id))).limit(1)
    mode_result = await db.execute(mode_stmt)
    most_used = mode_result.scalar_one_or_none()
    
    return {
        "total_predictions": total,
        "avg_confidence": round(avg_conf, 4) if avg_conf else 0.0,
        "avg_latency_ms": round(avg_lat, 2) if avg_lat else 0.0,
        "most_used_model": most_used,
    }


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**error_responses},
    summary="Delete a user — admin only",
)
async def delete_user(
    user_id: int,
    db:      AsyncSession   = Depends(get_db),
    _admin:  dict[str, Any] = Depends(require_admin),
):
    await user_crud.delete_user(db, user_id)


@router.get(
    "/{user_id}/predictions",
    response_model=UserWithPredictions,
    responses={**error_responses},
    summary="Get user's prediction history — admin or own",
)
async def get_user_predictions(
    user_id:      int,
    db:           AsyncSession   = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    await verify_resource_owner(user_id, current_user)
    return await user_crud.get_user_with_predictions(db, user_id)
