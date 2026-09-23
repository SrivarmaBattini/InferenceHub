# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    secret_key: str = "super_secret_temporary_key_replace_me_in_prod!"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Redis params
    redis_url:         str = "redis://localhost:6379/0"
    cache_default_ttl: int = 300

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
