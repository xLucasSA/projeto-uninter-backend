from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from raizes_api.application.ports.relogio import Relogio
from raizes_api.infrastructure.auditoria import GravadorAuditoriaSql
from raizes_api.infrastructure.outbox import GravadorOutboxSql
from raizes_api.infrastructure.repositories.autenticacao import (
    RepositorioDispositivosSql,
    RepositorioFuncionariosSql,
    RepositorioRefreshTokensSql,
)
from raizes_api.infrastructure.repositories.catalogo import RepositorioCatalogoSql, RepositorioEstoqueSql
from raizes_api.infrastructure.repositories.clientes import RepositorioClientesSql
from raizes_api.infrastructure.repositories.fidelidade import RepositorioFidelidadeSql
from raizes_api.infrastructure.repositories.idempotencia import RepositorioIdempotenciaSql
from raizes_api.infrastructure.repositories.pagamentos import RepositorioPagamentosSql, RepositorioWebhooksSql
from raizes_api.infrastructure.repositories.pedidos import RepositorioPedidosSql


class UnidadeDeTrabalhoSqlAlchemy:
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

    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession], relogio: Relogio) -> None:
        self._fabrica_sessoes = fabrica_sessoes
        self._relogio = relogio
        self._sessao: AsyncSession | None = None

    @property
    def sessao(self) -> AsyncSession:
        if self._sessao is None:
            raise RuntimeError("A Unit of Work só pode ser usada dentro de `async with`.")
        return self._sessao

    async def __aenter__(self) -> Self:
        sessao = self._fabrica_sessoes()
        self._sessao = sessao
        self.auditoria = GravadorAuditoriaSql(sessao, self._relogio)
        self.outbox = GravadorOutboxSql(sessao, self._relogio)
        self.clientes = RepositorioClientesSql(sessao)
        self.funcionarios = RepositorioFuncionariosSql(sessao)
        self.dispositivos = RepositorioDispositivosSql(sessao)
        self.refresh_tokens = RepositorioRefreshTokensSql(sessao)
        self.catalogo = RepositorioCatalogoSql(sessao)
        self.estoque = RepositorioEstoqueSql(sessao)
        self.pedidos = RepositorioPedidosSql(sessao)
        self.pagamentos = RepositorioPagamentosSql(sessao)
        self.webhooks = RepositorioWebhooksSql(sessao)
        self.fidelidade = RepositorioFidelidadeSql(sessao)
        self.idempotencia = RepositorioIdempotenciaSql(sessao)
        return self

    async def __aexit__(
        self,
        tipo_excecao: type[BaseException] | None,
        excecao: BaseException | None,
        rastreamento: TracebackType | None,
    ) -> None:
        await self.sessao.rollback()
        await self.sessao.close()
        self._sessao = None

    async def commit(self) -> None:
        await self.sessao.commit()
