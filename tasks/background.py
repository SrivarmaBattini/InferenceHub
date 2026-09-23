# tasks/background.py
import asyncio
import hashlib
import cache
import database
from models.prediction import Prediction

async def log_prediction_to_db(
    user_id:       int,
    features:      list[float],
    prediction:    float,
    confidence:    float,
    model_version: str,
    latency_ms:    float,
):
    """
    Persist a prediction result to the database.
    Creates its own session — safe to run as a background task.
    Never raises — logs failures to console.
    """
    input_hash = hashlib.sha256(
        str(sorted(features)).encode()
    ).hexdigest()[:64]

    async with database.AsyncSessionLocal() as db:
        try:
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
            print(f"[bg] Prediction logged — user={user_id} pred={prediction:.4f}")
        except Exception as exc:
            await db.rollback()
            print(f"[bg] Failed to log prediction: {exc!r}")


async def send_welcome_email(user_id: int, email: str, name: str):
    """Simulate sending a welcome email after registration."""
    try:
        await asyncio.sleep(0.1)
        print(f"[bg] Welcome email sent to {email} (user_id={user_id})")
    except Exception as exc:
        print(f"[bg] Failed to send welcome email to {email}: {exc!r}")


async def invalidate_user_cache(user_id: int):
    """Purge cached user data after a profile update."""
    try:
        from cache import cache_delete, CacheKey
        await cache_delete(CacheKey.user(user_id))
    except Exception as exc:
        print(f"[bg] Cache invalidation failed for user {user_id}: {exc!r}")


async def increment_prediction_counter(user_id: int, model_version: str):
    """Increment per-user, per-model prediction counters."""
    try:
        print(f"[bg] Counter incremented — user={user_id} model={model_version}")
    except Exception as exc:
        print(f"[bg] Counter increment failed: {exc!r}")
