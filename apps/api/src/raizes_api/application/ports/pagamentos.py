import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from raizes_api.domain.pagamentos.pagamento import Pagamento


class RepositorioPagamentos(Protocol):
    async def adicionar(self, pagamento: Pagamento) -> None: ...

    async def obter(self, pagamento_id: uuid.UUID) -> Pagamento | None:
        """Sem bloqueio: quem altera o pagamento bloqueia antes o pedido dele."""
        ...

    async def ativo_do_pedido(self, pedido_id: uuid.UUID) -> Pagamento | None:
        """O pagamento PENDENTE ou APROVADO do pedido, se houver (no máximo um, pelo índice único parcial)."""
        ...

    async def atualizar(self, pagamento: Pagamento) -> None: ...


@dataclass(frozen=True, slots=True)
class WebhookRecebido:
    event_id: uuid.UUID
    transacao_externa_id: str
    tipo: str
    hash_do_corpo: str
    recebido_em: datetime


class RepositorioWebhooks(Protocol):
    async def registrar(self, webhook: WebhookRecebido) -> bool:
        """True na primeira entrega do `eventId`; False se ele já foi recebido.

        Uma entrega concorrente do mesmo evento espera o commit (ou rollback) da primeira.
        """
        ...
