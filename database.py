# database.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from config import get_settings

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./inferencehub.db",
)

# ── Engine 
engine = create_async_engine(
    DATABASE_URL,
    echo        = os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_size   = int(os.getenv("DB_POOL_SIZE",   "10")),
    max_overflow= int(os.getenv("DB_MAX_OVERFLOW", "20")),
) if "postgresql" in DATABASE_URL else create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# ── Session factory 
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # keep attributes readable after commit
)


# ── Base class for all ORM models
class Base(DeclarativeBase):
    pass


# ── Async DB dependency 
async def get_db():
    """
    Yield an AsyncSession per request.
    Rolls back on any exception, always closes on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# ── Redis ─────────────────────────────────────────────────────────────────────
settings = get_settings()
redis_client: aioredis.Redis | None = None

def get_redis():
    if redis_client is None:
        raise RuntimeError("Redis not initialised")
    return redis_client

import ml.registry as model_registry_module
from ml.registry import ModelRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    await redis_client.ping()
    print("[startup] Redis connected")

    registry = ModelRegistry(max_workers=4)
    registry.load("regressor_v1", "ml_models/regressor_v1.joblib")
    registry.load("regressor_v2", "ml_models/regressor_v2.joblib")
    model_registry_module.registry = registry
    print("[startup] Models loaded")

    yield

    await redis_client.aclose()
    print("[shutdown] Redis disconnected")
    registry.shutdown()
    print("[shutdown] Model registry shut down")
        # session.close() is called automatically by async with