import json
from typing import Any
from database import get_redis
from config import get_settings

settings = get_settings()

class CacheKey:
    @staticmethod
    def user(user_id: int):
        return f"user:{user_id}"

    @staticmethod
    def prediction(input_hash: str, model_version: str):
        return f"prediction:{model_version}:{input_hash}"

    @staticmethod
    def user_predictions(user_id: int, skip: int, limit: int):
        return f"user_predictions:{user_id}:{skip}:{limit}"

    @staticmethod
    def admin_stats():
        return "admin:stats"

async def cache_get(key: str):
    try:
        redis  = get_redis()
        cached = await redis.get(key)
        if cached is None:
            return None
        return json.loads(cached)
    except Exception as exc:
        print(f"[cache] GET error for key={key!r}: {exc!r}")
        return None

async def cache_set(key: str, value: Any, ttl: int | None = None):
    try:
        redis    = get_redis()
        payload  = json.dumps(value, default=str)
        await redis.set(key, payload, ex=ttl or settings.cache_default_ttl)
    except Exception as exc:
        print(f"[cache] SET error for key={key!r}: {exc!r}")

async def cache_delete(key: str):
    try:
        redis = get_redis()
        await redis.delete(key)
        print(f"[cache] Invalidated key={key!r}")
    except Exception as exc:
        print(f"[cache] DELETE error for key={key!r}: {exc!r}")

async def cache_delete_pattern(pattern: str):
    try:
        redis = get_redis()
        async for key in redis.scan_iter(match=pattern):
            await redis.delete(key)
        print(f"[cache] Invalidated pattern={pattern!r}")
    except Exception as exc:
        print(f"[cache] Pattern delete error for {pattern!r}: {exc!r}")
