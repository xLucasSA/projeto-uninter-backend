"""Portas do lado de consulta (CQRS).

A implementação vem de `READ_MODEL_SOURCE`: banco de escrita ou read model (T3).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.domain.catalogo.catalogo import CategoriaProduto, OfertaNaUnidade
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.fidelidade.lancamento import TipoLancamento
from raizes_api.domain.pagamentos.pagamento import FormaPagamento, StatusPagamento
from raizes_api.domain.pedidos.acesso import VinculosDoPedido
from raizes_api.domain.pedidos.status import StatusPedido


@dataclass(frozen=True, slots=True)
class UnidadeResumo:
    id: int
    codigo: str
    nome: str
    cidade: str
    uf: str
    regiao: str
    tipo: str


@dataclass(frozen=True, slots=True)
class ProdutoResumo:
    id: int
    sku: str
    nome: str
    descricao: str
    categoria: CategoriaProduto


@dataclass(frozen=True, slots=True)
class OfertaDeCardapio:
    oferta: OfertaNaUnidade
    descricao: str
    categoria: CategoriaProduto
    quantidade_em_estoque: int


@dataclass(frozen=True, slots=True)
class SaldoEstoque:
    produto_id: int
    sku: str
    nome_produto: str
    quantidade: int
    atualizado_em: datetime


@dataclass(frozen=True, slots=True)
class FiltroPedidos:
    """`unidades` None = todas as unidades (cliente filtrado por `cliente_id`, ou MATRIZ)."""

    unidades: frozenset[int] | None
    cliente_id: uuid.UUID | None = None
    unidade_id: int | None = None
    canal: CanalPedido | None = None
    status: StatusPedido | None = None
    inicio: datetime | None = None
    fim: datetime | None = None


@dataclass(frozen=True, slots=True)
class PedidoResumo:
    id: uuid.UUID
    unidade_id: int
    canal: CanalPedido
    status: StatusPedido
    total: Decimal
    criado_em: datetime


@dataclass(frozen=True, slots=True)
class ItemDetalhe:
    produto_id: int
    nome_produto: str
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class PedidoDetalhe:
    id: uuid.UUID
    unidade_id: int
    canal: CanalPedido
    status: StatusPedido
    itens: tuple[ItemDetalhe, ...]
    total: Decimal
    observacao: str | None
    criado_em: datetime
    atualizado_em: datetime
    vinculos: VinculosDoPedido

    @property
    def cliente_identificado(self) -> bool:
        return self.vinculos.cliente_id is not None


@dataclass(frozen=True, slots=True)
class MudancaDeStatus:
    status_anterior: StatusPedido | None
    status_novo: StatusPedido
    ator_tipo: TipoAtor
    motivo: str | None
    ocorrido_em: datetime


@dataclass(frozen=True, slots=True)
class PagamentoResumo:
    id: uuid.UUID
    pedido_id: uuid.UUID
    status: StatusPagamento
    forma: FormaPagamento
    valor: Decimal
    motivo_recusa: str | None
    tentativas: int
    solicitado_em: datetime
    concluido_em: datetime | None


@dataclass(frozen=True, slots=True)
class LancamentoResumo:
    pedido_id: uuid.UUID
    tipo: TipoLancamento
    pontos: int
    criado_em: datetime


@dataclass(frozen=True, slots=True)
class FiltroAuditoria:
    """`unidades` None = toda a rede (MATRIZ). Com escopo, registros sem unidade ficam de fora."""

    unidades: frozenset[int] | None
    entidade: str | None = None
    entidade_id: str | None = None
    acao: str | None = None
    unidade_id: int | None = None
    inicio: datetime | None = None
    fim: datetime | None = None


@dataclass(frozen=True, slots=True)
class RegistroDaTrilha:
    """Linha de `vendas.auditoria` como sai na consulta: sem IP."""

    id: uuid.UUID
    ocorrido_em: datetime
    ator_tipo: TipoAtor
    ator_id: str
    acao: str
    entidade: str
    entidade_id: str
    unidade_id: int | None
    dados: dict[str, Any]
    request_id: str | None


class LeituraCatalogo(Protocol):
    async def listar_unidades(self, paginacao: Paginacao) -> Pagina[UnidadeResumo]: ...

    async def obter_unidade(self, unidade_id: int) -> UnidadeResumo | None:
        """Só unidades ativas: as inativas não aparecem para os canais."""
        ...

    async def ofertas_da_unidade(
        self, unidade_id: int, categoria: CategoriaProduto | None
    ) -> list[OfertaDeCardapio]: ...

    async def listar_produtos(
        self, categoria: CategoriaProduto | None, paginacao: Paginacao
    ) -> Pagina[ProdutoResumo]: ...

    async def obter_produto(self, produto_id: int) -> ProdutoResumo | None: ...


class LeituraEstoque(Protocol):
    async def saldos(self, unidade_id: int, paginacao: Paginacao) -> Pagina[SaldoEstoque]: ...


class LeituraPedidos(Protocol):
    async def listar(self, filtro: FiltroPedidos, paginacao: Paginacao) -> Pagina[PedidoResumo]: ...

    async def obter(self, pedido_id: uuid.UUID) -> PedidoDetalhe | None: ...

    async def historico(self, pedido_id: uuid.UUID) -> list[MudancaDeStatus]: ...


class LeituraPagamentos(Protocol):
    async def do_pedido(self, pedido_id: uuid.UUID) -> list[PagamentoResumo]:
        """Todas as tentativas do pedido, da mais antiga para a mais recente."""
        ...


class LeituraFidelidade(Protocol):
    async def saldo(self, cliente_id: uuid.UUID) -> int: ...

    async def extrato(self, cliente_id: uuid.UUID, paginacao: Paginacao) -> Pagina[LancamentoResumo]: ...


class LeituraAuditoria(Protocol):
    async def listar(self, filtro: FiltroAuditoria, paginacao: Paginacao) -> Pagina[RegistroDaTrilha]: ...
