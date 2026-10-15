from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VibeFinance API"
    app_environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_key: str | None = None
    market_data_mode: Literal["demo", "live"] = "live"
    filing_allowed_hosts: str = "nseindia.com,bseindia.com,sebi.gov.in,ril.com"
    filing_max_download_mb: int = 25
    filing_storage_bucket: str = "financial-filings"
    sec_user_agent: str | None = None
    llm_provider: Literal["openai", "anthropic"] | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    @property
    def filing_host_allowlist(self) -> set[str]:
        return {
            host.strip().lower() for host in self.filing_allowed_hosts.split(",") if host.strip()
        }

    @property
    def supabase_backend_key(self) -> str | None:
        """Prefer server-only keys while retaining legacy variable compatibility."""
        return self.supabase_secret_key or self.supabase_service_role_key or self.supabase_key

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
