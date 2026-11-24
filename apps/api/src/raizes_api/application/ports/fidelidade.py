import uuid
from typing import Protocol

from raizes_api.domain.fidelidade.lancamento import LancamentoFidelidade


class RepositorioFidelidade(Protocol):
    async def adicionar(self, lancamento: LancamentoFidelidade) -> None: ...

    async def credito_do_pedido(self, pedido_id: uuid.UUID) -> LancamentoFidelidade | None: ...
