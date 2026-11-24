import uuid
from dataclasses import dataclass
from typing import Protocol

from raizes_api.domain.compartilhado.dinheiro import Dinheiro


@dataclass(frozen=True, slots=True)
class SolicitacaoPagamento:
    """O que vai ao gateway. `pagamento_id` é a Idempotency-Key: repetir a chamada é seguro."""

    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    valor: Dinheiro
    token_pagamento: str


@dataclass(frozen=True, slots=True)
class TransacaoAceita:
    transacao_id: str
    tentativas: int


class GatewayPagamento(Protocol):
    async def solicitar(self, solicitacao: SolicitacaoPagamento) -> TransacaoAceita:
        """Pede a cobrança; o resultado chega depois, pelo webhook.

        Lança `GatewayIndisponivel` (com o número de tentativas) quando as retentativas se esgotam.
        """
        ...
