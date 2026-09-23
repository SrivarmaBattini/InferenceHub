# crud/prediction.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.prediction import Prediction


async def log_prediction(
    db: AsyncSession,
    user_id: int,
    input_hash: str,
    prediction: float,
    confidence: float,
    model_version: str,
    latency_ms: float,
):
    """Insert a new prediction log row and return it."""
    row = Prediction(
        user_id       = user_id,
        input_hash    = input_hash,
        prediction    = prediction,
        confidence    = confidence,
        model_version = model_version,
        latency_ms    = latency_ms,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_predictions_for_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
):
    """Return paginated predictions for one user plus total count."""
    page_stmt = (
        select(Prediction)
        .where(Prediction.user_id == user_id)
        .order_by(Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_stmt = (
        select(func.count())
        .select_from(Prediction)
        .where(Prediction.user_id == user_id)
    )

    page_result  = await db.execute(page_stmt)
    count_result = await db.execute(count_stmt)

    return list(page_result.scalars().all()), count_result.scalar_one()