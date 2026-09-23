# routers/admin.py
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies.auth import require_admin
from dependencies.pagination import PaginationParams
from schemas.user import UserListResponse
from schemas.errors import error_responses
import crud.user as user_crud

# Every route in this router automatically requires admin role
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],   # ← applied to ALL routes below
)

@router.get(
    "/users",
    response_model=UserListResponse,
    responses={**error_responses},
    summary="Admin: list all users with full details",
)
async def admin_list_users(
    pagination: PaginationParams = Depends(PaginationParams),
    db:         AsyncSession     = Depends(get_db),
):
    users, total = await user_crud.get_users(db, pagination.skip, pagination.limit)
    return {"total": total, "users": users}

from cache import CacheKey, cache_get, cache_set
@router.get(
    "/stats",
    summary="Get system-wide statistics",
)
async def admin_stats(db: AsyncSession = Depends(get_db)):
    cache_key = CacheKey.admin_stats()
    cached    = await cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    from sqlalchemy import select, func
    from models.user import User
    from models.prediction import Prediction

    user_count = await db.scalar(select(func.count()).select_from(User))
    pred_count = await db.scalar(select(func.count()).select_from(Prediction))

    result = {"total_users": user_count, "total_predictions": pred_count, "cached": False}
    await cache_set(cache_key, result, ttl=60)
    return result

@router.get(
    "/model-stats",
    summary="Get model specific statistics",
)
async def admin_model_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from models.prediction import Prediction
    stmt = select(
        Prediction.model_version, 
        func.avg(Prediction.latency_ms).label('avg_latency'),
        func.count(Prediction.id).label('total')
    ).group_by(Prediction.model_version)
    
    result = await db.execute(stmt)
    records = []
    for row in result.all():
        records.append({
            "model_version": row.model_version,
            "avg_latency_ms": round(row.avg_latency, 2),
            "total_predictions": row.total
        })
    return {"models": records}

@router.patch(
    "/users/{user_id}/deactivate",
    summary="Admin: deactivate a user account",
)
async def deactivate_user(
    user_id: int,
    db:      AsyncSession = Depends(get_db),
):
    from crud.user import get_user_by_id
    user           = await get_user_by_id(db, user_id)
    user.is_active = False
    await db.commit()
    return {"message": f"User {user_id} deactivated"}

@router.patch(
    "/users/{user_id}/verify",
    summary="Admin: mark a user as verified",
)
async def verify_user(
    user_id: int,
    db:      AsyncSession = Depends(get_db),
):
    from crud.user import get_user_by_id
    user              = await get_user_by_id(db, user_id)
    user.is_verified  = True
    await db.commit()
    return {"message": f"User {user_id} verified"}

from schemas.user import UpdateRoleRequest

@router.patch("/users/{user_id}/role", summary="Admin: change a user's role")
async def change_user_role(
    user_id: int,
    body:    UpdateRoleRequest,
    db:      AsyncSession = Depends(get_db),
):
    from crud.user import get_user_by_id
    from models.user import UserRole
    user      = await get_user_by_id(db, user_id)
    user.role = UserRole(body.role)
    await db.commit()
    return {"message": f"User {user_id} role updated to {body.role}"}

from logger import get_recent_logs
from middleware.logging import get_endpoint_metrics

@router.get("/logs/recent", summary="Admin: recent log events")
async def recent_logs() -> dict:
    return {"logs": get_recent_logs()}

@router.get("/metrics", summary="Admin: get endpoint metrics")
async def metrics() -> dict:
    return get_endpoint_metrics()
