# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# ── Import your app's Base and ALL models 
# Every model must be imported here so Alembic can see it.
# If you add a new model file, add its import here too.
from database import Base
import models.user        # registers User with Base.metadata
import models.prediction  # registers Prediction with Base.metadata
import models.tag         # registers Tag with Base.metadata

# ── Alembic config object
config = context.config
import os

def get_sync_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./inferencehub.db")
    return (
        url
        .replace("postgresql+asyncpg://", "postgresql+psycopg://")
        .replace("sqlite+aiosqlite://",   "sqlite://")
    )

config.set_main_option("sqlalchemy.url", get_sync_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what autogenerate compares against — your current models
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations without a live DB connection (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,       # detect column type changes
        compare_server_default=True,  # detect default value changes
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Run migrations using an async engine — required for async SQLAlchemy."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())