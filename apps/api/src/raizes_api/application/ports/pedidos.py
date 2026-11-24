import uuid
from typing import Protocol

from raizes_api.domain.pedidos.pedido import MudancaDeStatusPedido, Pedido


class RepositorioPedidos(Protocol):
    async def adicionar(self, pedido: Pedido) -> None:
        """Grava o pedido, os itens e a primeira linha do histórico de status."""
        ...

    async def obter_para_atualizacao(self, pedido_id: uuid.UUID) -> Pedido | None:
        """Bloqueia o pedido até o fim da transação (`SELECT ... FOR UPDATE`).

        Pagamento, webhook, cancelamento e mudança de status do mesmo pedido passam por esse bloqueio,
        sempre antes de tocar no pagamento: dois webhooks concorrentes não aplicam duas transições.
        """
        ...

    async def registrar_mudanca(self, pedido: Pedido, mudanca: MudancaDeStatusPedido) -> None:
        """Grava o status novo e a linha do histórico."""
        ...
