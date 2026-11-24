"""Assinatura dos webhooks: HMAC-SHA256 de "{timestamp}.{corpo_bruto}" (guideline 08).

O timestamp entra na mensagem assinada para o receptor recusar reenvios antigos (janela de ±300 s).
"""

import hashlib
import hmac

PREFIXO = "sha256="
HEADER_EVENTO = "X-Event-Id"
HEADER_TIMESTAMP = "X-Webhook-Timestamp"
HEADER_ASSINATURA = "X-Signature"


def assinar(corpo: bytes, timestamp: int, segredo: str) -> str:
    mensagem = f"{timestamp}.".encode() + corpo
    return PREFIXO + hmac.new(segredo.encode(), mensagem, hashlib.sha256).hexdigest()


def cabecalhos_do_webhook(*, event_id: str, corpo: bytes, timestamp: int, segredo: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        HEADER_EVENTO: event_id,
        HEADER_TIMESTAMP: str(timestamp),
        HEADER_ASSINATURA: assinar(corpo, timestamp, segredo),
    }
