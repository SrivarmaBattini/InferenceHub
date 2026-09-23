# security.py
import bcrypt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from config import get_settings

settings = get_settings()

def hash_password(plain_password: str):
    """Return a bcrypt hash of the password."""
    pwd_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    """Return True if plain_password matches the stored hash."""
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except ValueError:
        return False

def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
):
    """Create a signed JWT."""
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_access_token(token: str):
    """Decode and verify a JWT."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )

async def revoke_token(jti: str, ttl_seconds: int):
    try:
        from database import get_redis
        redis = get_redis()
        await redis.set(f"revoked_token:{jti}", "1", ex=ttl_seconds)
    except Exception as exc:
        print(f"Rejection flush failed: {exc}")

async def is_token_revoked(jti: str):
    try:
        from database import get_redis
        redis = get_redis()
        result = await redis.get(f"revoked_token:{jti}")
        return result is not None
    except Exception:
        return False
