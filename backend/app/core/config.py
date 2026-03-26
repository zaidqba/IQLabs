"""
IQ-RAD Application Configuration
Loaded from environment variables / .env file.
All secrets are required — no defaults for security-critical values.
"""
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── Application ──────────────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 2
    app_version: str = "1.0.0"
    cors_origins: str = "http://localhost:3000"

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str

    # ─── Rotem Device Connectors ──────────────────────────────────────────────
    rotem_stack_host: str = "10.0.0.160"
    rotem_stack_port: int = 4001
    rotem_dpu3_host: str = "10.0.0.160"
    rotem_dpu3_port: int = 5000
    connection_unit_host: str = "localhost"
    connection_unit_port: int = 15386
    poll_interval_s: int = 10
    connect_timeout_s: float = 5.0
    read_timeout_s: float = 8.0

    # ─── Security ─────────────────────────────────────────────────────────────
    jwt_secret: str
    hmac_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_hours: int = 8
    login_max_failures: int = 5

    # ─── NTP ──────────────────────────────────────────────────────────────────
    ntp_server: str = "pool.ntp.org"
    max_ntp_drift_ms: int = 500

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("jwt_secret", "hmac_secret")
    @classmethod
    def secrets_must_not_be_placeholder(cls, v: str) -> str:
        if "placeholder" in v.lower() or "change-me" in v.lower() or v == "":
            raise ValueError(
                "JWT_SECRET and HMAC_SECRET must be set to secure random values. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
