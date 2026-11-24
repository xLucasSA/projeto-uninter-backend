import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from raizes_api.domain.compartilhado.atores import AtorAutenticado, TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.dinheiro import Dinheiro
from raizes_api.domain.pedidos.acesso import VinculosDoPedido
from raizes_api.domain.pedidos.status import StatusPedido, exigir_transicao

QUANTIDADE_MINIMA_POR_ITEM = 1
QUANTIDADE_MAXIMA_POR_ITEM = 20
LIMITE_ITENS_POR_PEDIDO = 30


@dataclass(frozen=True, slots=True)
class ItemPedido:
    """`nome_produto` e `preco_unitario` são congelados na criação: mudar o cardápio não altera pedidos."""

    produto_id: int
    nome_produto: str
    quantidade: int
    preco_unitario: Dinheiro

    def __post_init__(self) -> None:
        if not QUANTIDADE_MINIMA_POR_ITEM <= self.quantidade <= QUANTIDADE_MAXIMA_POR_ITEM:
            raise ValueError(f"Quantidade fora do limite: {self.quantidade}")

    @property
    def subtotal(self) -> Dinheiro:
        return self.preco_unitario.multiplicado_por(self.quantidade)


@dataclass(frozen=True, slots=True)
class Autoria:
    tipo: TipoAtor
    id: str

    @classmethod
    def de(cls, ator: AtorAutenticado) -> "Autoria":
        return cls(tipo=ator.tipo, id=ator.id)


@dataclass(frozen=True, slots=True)
class MudancaDeStatusPedido:
    status_anterior: StatusPedido
    status_novo: StatusPedido
    autoria: Autoria
    motivo: str | None
    ocorrido_em: datetime


@dataclass(eq=False, slots=True)
class Pedido:
    id: uuid.UUID
    unidade_id: int
    canal: CanalPedido
    status: StatusPedido
    itens: tuple[ItemPedido, ...]
    cliente_id: uuid.UUID | None
    criado_por: Autoria
    observacao: str | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def criar(
        cls,
        *,
        unidade_id: int,
        canal: CanalPedido,
        itens: Sequence[ItemPedido],
        cliente_id: uuid.UUID | None,
        criado_por: AtorAutenticado,
        observacao: str | None,
        agora: datetime,
    ) -> "Pedido":
        _validar_itens(itens)
        return cls(
            id=uuid.uuid4(),
            unidade_id=unidade_id,
            canal=canal,
            status=StatusPedido.AGUARDANDO_PAGAMENTO,
            itens=tuple(itens),
            cliente_id=cliente_id,
            criado_por=Autoria.de(criado_por),
            observacao=observacao,
            criado_em=agora,
            atualizado_em=agora,
        )

    @property
    def total(self) -> Dinheiro:
        return Dinheiro.somar(item.subtotal for item in self.itens)

    @property
    def cliente_identificado(self) -> bool:
        return self.cliente_id is not None

    @property
    def vinculos(self) -> VinculosDoPedido:
        return VinculosDoPedido(
            unidade_id=self.unidade_id,
            cliente_id=self.cliente_id,
            criado_por_tipo=self.criado_por.tipo,
            criado_por_id=self.criado_por.id,
        )

    @property
    def aguarda_pagamento(self) -> bool:
        return self.status is StatusPedido.AGUARDANDO_PAGAMENTO

    def mudar_status(
        self, novo: StatusPedido, ator: AtorAutenticado, *, agora: datetime, motivo: str | None = None
    ) -> MudancaDeStatusPedido:
        """Única forma de mudar o status: a máquina de estados decide se a transição existe e quem pode."""
        exigir_transicao(self.status, novo, ator)
        mudanca = MudancaDeStatusPedido(
            status_anterior=self.status,
            status_novo=novo,
            autoria=Autoria.de(ator),
            motivo=motivo,
            ocorrido_em=agora,
        )
        self.status = novo
        self.atualizado_em = agora
        return mudanca

    def itens_em_ordem_de_reserva(self) -> list[tuple[int, ItemPedido]]:
        """Itens com a posição original, ordenados por `produto_id`.

        Dois pedidos com os mesmos produtos travam as linhas de estoque na mesma ordem
        e não entram em deadlock.
        """
        return sorted(enumerate(self.itens), key=lambda posicao_e_item: posicao_e_item[1].produto_id)


def _validar_itens(itens: Sequence[ItemPedido]) -> None:
    if not 1 <= len(itens) <= LIMITE_ITENS_POR_PEDIDO:
        raise ValueError(f"Pedido precisa de 1 a {LIMITE_ITENS_POR_PEDIDO} itens.")
    if len({item.produto_id for item in itens}) != len(itens):
        raise ValueError("Pedido com produto repetido.")
