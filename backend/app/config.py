from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VibeFinance API"
    app_environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sqlalchemy_database_url(database_url: str) -> str:
    """Return a Psycopg 3 URL without exposing or otherwise changing credentials."""
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    raise ValueError("DATABASE_URL must use a PostgreSQL connection scheme")
