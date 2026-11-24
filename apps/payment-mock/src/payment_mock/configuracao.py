from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TAMANHO_MINIMO_SEGREDO = 32


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True, validate_by_name=True)

    segredo_webhook: str = Field(validation_alias="PAYMENT_WEBHOOK_SECRET")
    url_webhook: str = Field(
        default="http://api:8001/webhooks/pagamentos", validation_alias="PAYMENT_WEBHOOK_URL"
    )
    atraso_webhook_ms: int = Field(default=500, ge=0, validation_alias="PAYMENT_MOCK_WEBHOOK_DELAY_MS")
    segundos_sem_resposta: float = Field(
        default=10, ge=0, description="Quanto o cenário tok_timeout demora para responder."
    )
    esperas_de_reenvio: tuple[float, ...] = Field(
        default=(1, 2, 4), description="Espera antes de cada reenvio do webhook (entrega at-least-once)."
    )
    timeout_entrega_segundos: float = Field(default=5, gt=0)

    @field_validator("segredo_webhook")
    @classmethod
    def _segredo_forte(cls, segredo: str) -> str:
        if len(segredo) < TAMANHO_MINIMO_SEGREDO:
            raise ValueError(
                f"PAYMENT_WEBHOOK_SECRET precisa ter pelo menos {TAMANHO_MINIMO_SEGREDO} caracteres."
            )
        return segredo
