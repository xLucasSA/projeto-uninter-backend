from datetime import timedelta
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TAMANHO_MINIMO_SEGREDO_JWT_BYTES = 32
TAMANHO_MINIMO_SEGREDO_WEBHOOK = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    database_url: str = Field(validation_alias="API_DATABASE_URL")
    read_model_source: Literal["write", "read"] = Field(default="write", validation_alias="READ_MODEL_SOURCE")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    seed_demo: bool = Field(default=False, validation_alias="SEED_DEMO")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_access_ttl_seconds: int = Field(default=900, gt=0, validation_alias="JWT_ACCESS_TTL_SECONDS")
    jwt_refresh_ttl_days: int = Field(default=30, gt=0, validation_alias="JWT_REFRESH_TTL_DAYS")
    jwt_device_ttl_seconds: int = Field(default=43200, gt=0, validation_alias="JWT_DEVICE_TTL_SECONDS")

    payment_gateway_url: str = Field(
        default="http://payment-mock:8002", validation_alias="PAYMENT_GATEWAY_URL"
    )
    payment_gateway_timeout_seconds: float = Field(
        default=2, gt=0, validation_alias="PAYMENT_GATEWAY_TIMEOUT_SECONDS"
    )
    payment_gateway_max_retries: int = Field(default=2, ge=0, validation_alias="PAYMENT_GATEWAY_MAX_RETRIES")
    payment_webhook_secret: str = Field(
        min_length=TAMANHO_MINIMO_SEGREDO_WEBHOOK, validation_alias="PAYMENT_WEBHOOK_SECRET"
    )

    @field_validator("jwt_secret")
    @classmethod
    def _segredo_forte(cls, segredo: str) -> str:
        if len(segredo.encode()) < TAMANHO_MINIMO_SEGREDO_JWT_BYTES:
            raise ValueError(f"JWT_SECRET precisa ter pelo menos {TAMANHO_MINIMO_SEGREDO_JWT_BYTES} bytes.")
        return segredo

    def origens_cors(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origins.split(",") if origem.strip()]

    def validade_acesso(self) -> timedelta:
        return timedelta(seconds=self.jwt_access_ttl_seconds)

    def validade_refresh(self) -> timedelta:
        return timedelta(days=self.jwt_refresh_ttl_days)

    def validade_dispositivo(self) -> timedelta:
        return timedelta(seconds=self.jwt_device_ttl_seconds)
