"""Autenticação do webhook do gateway: HMAC-SHA256 de "{timestamp}.{corpo_bruto}" (guideline 08)."""

import hashlib
import hmac
from datetime import timedelta
from typing import NoReturn

import structlog

from raizes_api.application.erros import AssinaturaWebhookInvalida
from raizes_api.application.ports.relogio import Relogio

logger = structlog.get_logger(__name__)

PREFIXO_ASSINATURA = "sha256="
JANELA_DO_TIMESTAMP = timedelta(seconds=300)


class VerificadorAssinaturaHmac:
    def __init__(self, segredo: str, relogio: Relogio, janela: timedelta = JANELA_DO_TIMESTAMP) -> None:
        self._segredo = segredo.encode()
        self._relogio = relogio
        self._janela = janela

    def verificar(self, corpo: bytes, timestamp: str | None, assinatura: str | None) -> None:
        """A assinatura cobre o corpo bruto, antes de qualquer parse; o timestamp limita o replay a ±300 s."""
        if timestamp is None or assinatura is None:
            self._recusar("cabecalho_ausente")
        instante = _segundos(timestamp)
        if instante is None:
            self._recusar("timestamp_invalido")
        if abs(self._relogio.agora().timestamp() - instante) > self._janela.total_seconds():
            self._recusar("timestamp_fora_da_janela")
        esperada = PREFIXO_ASSINATURA + assinar(corpo, timestamp, self._segredo)
        # compare_digest: o tempo da comparação não revela quantos caracteres conferem.
        if not hmac.compare_digest(esperada.encode(), assinatura.encode()):
            self._recusar("assinatura_invalida")

    @staticmethod
    def _recusar(motivo: str) -> NoReturn:
        # Log de segurança sem o payload: o corpo pode trazer dados do pedido.
        logger.warning("webhook_recusado", motivo=motivo)
        raise AssinaturaWebhookInvalida()


def assinar(corpo: bytes, timestamp: str, segredo: bytes) -> str:
    return hmac.new(segredo, timestamp.encode() + b"." + corpo, hashlib.sha256).hexdigest()


def _segundos(timestamp: str) -> int | None:
    return int(timestamp) if timestamp.isascii() and timestamp.isdigit() else None
