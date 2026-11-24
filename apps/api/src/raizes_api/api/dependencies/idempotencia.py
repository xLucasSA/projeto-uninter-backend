import uuid

from raizes_api.application.erros import IdempotencyKeyAusente

HEADER_IDEMPOTENCY_KEY = "Idempotency-Key"
HEADER_REPRODUZIDA = "Idempotent-Replayed"


def uuid_da_chave(valor: str | None) -> uuid.UUID:
    """Chamado no handler, depois da validação do corpo: corpo inválido sem chave responde 422, não 400."""
    if valor is None:
        raise IdempotencyKeyAusente()
    try:
        return uuid.UUID(valor)
    except ValueError as erro:
        raise IdempotencyKeyAusente("O header Idempotency-Key precisa ser um UUID.") from erro
