from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    app_name: str = "KnK Capital Terminal"
    knk_env: str = "local-demo"
    knk_timezone: str = "Asia/Singapore"
    knk_base_currency: str = "SGD"
    knk_reference_capital: str = "100000"
    database_url: str = Field(default="sqlite:///./knk_terminal.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    object_storage_endpoint: str | None = Field(default=None, alias="MINIO_ENDPOINT")
    object_storage_access_key: str | None = Field(default=None, alias="MINIO_ACCESS_KEY")
    object_storage_secret_key: str | None = Field(default=None, alias="MINIO_SECRET_KEY")
    object_storage_bucket: str = Field(default="knk-terminal-local", alias="OBJECT_STORAGE_BUCKET")
    object_storage_local_dir: str = Field(default=".knk-object-store", alias="OBJECT_STORAGE_LOCAL_DIR")
    fred_enabled: bool = Field(default=False, alias="FRED_ENABLED")
    fred_api_key: str | None = Field(default=None, alias="FRED_API_KEY")
    fred_base_url: str = Field(default="https://api.stlouisfed.org/fred", alias="FRED_BASE_URL")
    fred_request_timeout_seconds: float = Field(default=15.0, alias="FRED_REQUEST_TIMEOUT_SECONDS")
    fred_max_retries: int = Field(default=3, alias="FRED_MAX_RETRIES")
    sec_enabled: bool = Field(default=False, alias="SEC_ENABLED")
    sec_user_agent: str | None = Field(default=None, alias="SEC_USER_AGENT")
    openfigi_enabled: bool = Field(default=False, alias="OPENFIGI_ENABLED")
    openfigi_api_key: str | None = Field(default=None, alias="OPENFIGI_API_KEY")
    market_enabled: bool = Field(default=False, alias="MARKET_DATA_ENABLED")
    market_base_url: str | None = Field(default=None, alias="MARKET_DATA_BASE_URL")
    market_api_key: str | None = Field(default=None, alias="MARKET_DATA_API_KEY")
    options_enabled: bool = Field(default=False, alias="OPTIONS_DATA_ENABLED")
    options_base_url: str | None = Field(default=None, alias="OPTIONS_DATA_BASE_URL")
    options_api_key: str | None = Field(default=None, alias="OPTIONS_DATA_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
