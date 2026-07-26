"""Настройки приложения через Pydantic Settings (все значения — из ``.env``)."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    """Окружение запуска приложения."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"


class BotSettings(BaseSettings):
    """Параметры Telegram-бота."""

    model_config = SettingsConfigDict(env_prefix="BOT__", extra="ignore")

    token: SecretStr = Field(..., description="Токен бота от @BotFather")
    admin_ids: list[int] = Field(
        default_factory=list,
        description="Telegram ID владельцев с безусловными суперправами",
    )
    parse_mode: str = Field(default="HTML")
    drop_pending_updates: bool = Field(default=True)


class DatabaseSettings(BaseSettings):
    """Параметры подключения к PostgreSQL."""

    model_config = SettingsConfigDict(env_prefix="DB__", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="autosale")
    password: SecretStr = Field(default=SecretStr("autosale"))
    name: str = Field(default="autosale")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=10)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dsn(self) -> str:
        """Async DSN (asyncpg) для SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_dsn(self) -> str:
        """Синхронный DSN (psycopg) — используется Alembic при необходимости."""
        return (
            f"postgresql+psycopg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Параметры подключения к Redis (FSM-хранилище, throttling, кэш)."""

    model_config = SettingsConfigDict(env_prefix="REDIS__", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: SecretStr | None = Field(default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dsn(self) -> str:
        """DSN подключения к Redis."""
        auth = ""
        if self.password is not None and self.password.get_secret_value():
            auth = f":{self.password.get_secret_value()}@"
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class GeneralSettings(BaseSettings):
    """Общие настройки приложения."""

    model_config = SettingsConfigDict(env_prefix="APP__", extra="ignore")

    env: AppEnv = Field(default=AppEnv.PRODUCTION)
    log_level: str = Field(default="INFO")
    log_dir: Path = Field(default=Path("app/logs"))
    currency: str = Field(default="RUB")
    currency_symbol: str = Field(default="₽")
    page_size: int = Field(default=8, ge=1, le=50)
    dispute_window_hours: int = Field(default=24, ge=1)
    rate_limit_per_second: int = Field(default=3, ge=1)
    backup_dir: Path = Field(default=Path("backups"))
    backup_cron: str = Field(default="0 4 * * *")

    @property
    def is_testing(self) -> bool:
        return self.env is AppEnv.TESTING

    @property
    def is_development(self) -> bool:
        return self.env is AppEnv.DEVELOPMENT


class Settings(BaseSettings):
    """Корневой объект настроек, агрегирующий все подсистемы."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    bot: BotSettings = Field(default_factory=BotSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    app: GeneralSettings = Field(default_factory=GeneralSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть кэшированный синглтон настроек."""
    return Settings()
