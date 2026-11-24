from types import TracebackType
from typing import Protocol, Self

from raizes_api.application.ports.auditoria import GravadorAuditoria
from raizes_api.application.ports.autenticacao import (
    RepositorioDispositivos,
    RepositorioFuncionarios,
    RepositorioRefreshTokens,
)
from raizes_api.application.ports.catalogo import RepositorioCatalogo, RepositorioEstoque
from raizes_api.application.ports.clientes import RepositorioClientes
from raizes_api.application.ports.fidelidade import RepositorioFidelidade
from raizes_api.application.ports.idempotencia import RepositorioIdempotencia
from raizes_api.application.ports.outbox import GravadorOutbox
from raizes_api.application.ports.pagamentos import RepositorioPagamentos, RepositorioWebhooks
from raizes_api.application.ports.pedidos import RepositorioPedidos


class UnitOfWork(Protocol):
    """Uma transação por comando: `async with uow:` + `await uow.commit()`.

    Sair do bloco sem `commit()` (inclusive por exceção) desfaz tudo, auditoria e outbox incluídas.
    """

    auditoria: GravadorAuditoria
    outbox: GravadorOutbox
    clientes: RepositorioClientes
    funcionarios: RepositorioFuncionarios
    dispositivos: RepositorioDispositivos
    refresh_tokens: RepositorioRefreshTokens
    catalogo: RepositorioCatalogo
    estoque: RepositorioEstoque
    pedidos: RepositorioPedidos
    pagamentos: RepositorioPagamentos
    webhooks: RepositorioWebhooks
    fidelidade: RepositorioFidelidade
    idempotencia: RepositorioIdempotencia

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        tipo_excecao: type[BaseException] | None,
        excecao: BaseException | None,
        rastreamento: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
