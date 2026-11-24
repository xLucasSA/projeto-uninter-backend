import uuid
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, JsonValue, field_validator

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.api.schemas.tipos import DinheiroJson, TelefoneE164
from raizes_api.application.ports.idempotencia import RespostaGravada
from raizes_api.application.ports.leitura import MudancaDeStatus, PedidoDetalhe, PedidoResumo
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.pedidos.pedido import (
    LIMITE_ITENS_POR_PEDIDO,
    QUANTIDADE_MAXIMA_POR_ITEM,
    QUANTIDADE_MINIMA_POR_ITEM,
)
from raizes_api.domain.pedidos.status import STATUS_DA_OPERACAO, StatusPedido

STATUS_CRIADO = 201
STATUS_DO_PATCH: list[JsonValue] = [status.value for status in sorted(STATUS_DA_OPERACAO)]


class ItemPedidoRequest(SchemaBase):
    produto_id: int = Field(ge=1, examples=[10])
    quantidade: int = Field(ge=QUANTIDADE_MINIMA_POR_ITEM, le=QUANTIDADE_MAXIMA_POR_ITEM, examples=[2])


class IdentificacaoClienteRequest(SchemaBase):
    telefone: TelefoneE164


class CriarPedidoRequest(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "canalPedido": "TOTEM",
                    "unidadeId": 1,
                    "itens": [{"produtoId": 10, "quantidade": 2}],
                    "formaPagamento": "MOCK",
                    "identificacaoCliente": {"telefone": "+5581999990000"},
                    "observacao": "sem cebola",
                }
            ]
        }
    )

    canal_pedido: CanalPedido
    unidade_id: int = Field(ge=1)
    itens: list[ItemPedidoRequest] = Field(min_length=1, max_length=LIMITE_ITENS_POR_PEDIDO)
    forma_pagamento: Literal["MOCK"] = "MOCK"
    identificacao_cliente: IdentificacaoClienteRequest | None = Field(
        default=None, description="Só totem e balcão. Telefone sem cadastro gera pedido anônimo."
    )
    observacao: str | None = Field(default=None, max_length=200)

    @field_validator("itens")
    @classmethod
    def _sem_produto_repetido(cls, itens: list[ItemPedidoRequest]) -> list[ItemPedidoRequest]:
        if len({item.produto_id for item in itens}) != len(itens):
            raise ValueError("Cada produto deve aparecer uma única vez; some as quantidades.")
        return itens


class AtualizarStatusRequest(SchemaBase):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "EM_PREPARO", "motivo": None}]})

    status: StatusPedido = Field(
        description=(
            "Só `EM_PREPARO`, `PRONTO` ou `ENTREGUE`: os demais status vêm do pagamento ou do cancelamento."
        ),
        json_schema_extra={"enum": STATUS_DO_PATCH},
    )
    motivo: str | None = Field(default=None, max_length=200)

    @field_validator("status")
    @classmethod
    def _status_da_operacao(cls, status: StatusPedido) -> StatusPedido:
        if status not in STATUS_DA_OPERACAO:
            raise ValueError("Use EM_PREPARO, PRONTO ou ENTREGUE.")
        return status


class CancelarPedidoRequest(SchemaBase):
    model_config = ConfigDict(json_schema_extra={"examples": [{"motivo": "Cliente desistiu"}]})

    motivo: str = Field(min_length=3, max_length=200)


class ItemPedidoResponse(SchemaBase):
    produto_id: int = Field(examples=[10])
    nome_produto: str = Field(examples=["Tapioca de queijo coalho"])
    quantidade: int = Field(examples=[2])
    preco_unitario: DinheiroJson = Field(examples=[14.90])
    subtotal: DinheiroJson = Field(examples=[29.80])


class PedidoResponse(SchemaBase):
    """Nunca traz nome nem telefone do cliente: só se ele foi identificado (minimização, LGPD)."""

    pedido_id: uuid.UUID
    unidade_id: int = Field(examples=[1])
    canal_pedido: CanalPedido
    status: StatusPedido
    cliente_identificado: bool
    itens: list[ItemPedidoResponse]
    total: DinheiroJson = Field(examples=[29.80])
    observacao: str | None = None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, pedido: PedidoDetalhe) -> "PedidoResponse":
        return cls(
            pedido_id=pedido.id,
            unidade_id=pedido.unidade_id,
            canal_pedido=pedido.canal,
            status=pedido.status,
            cliente_identificado=pedido.cliente_identificado,
            itens=[
                ItemPedidoResponse(
                    produto_id=item.produto_id,
                    nome_produto=item.nome_produto,
                    quantidade=item.quantidade,
                    preco_unitario=item.preco_unitario,
                    subtotal=item.subtotal,
                )
                for item in pedido.itens
            ],
            total=pedido.total,
            observacao=pedido.observacao,
            criado_em=pedido.criado_em,
            atualizado_em=pedido.atualizado_em,
        )


class PedidoResumoResponse(SchemaBase):
    pedido_id: uuid.UUID
    unidade_id: int = Field(examples=[1])
    canal_pedido: CanalPedido
    status: StatusPedido
    total: DinheiroJson = Field(examples=[29.80])
    criado_em: datetime

    @classmethod
    def de(cls, pedido: PedidoResumo) -> "PedidoResumoResponse":
        return cls(
            pedido_id=pedido.id,
            unidade_id=pedido.unidade_id,
            canal_pedido=pedido.canal,
            status=pedido.status,
            total=pedido.total,
            criado_em=pedido.criado_em,
        )


class MudancaDeStatusResponse(SchemaBase):
    status_anterior: StatusPedido | None
    status_novo: StatusPedido
    ator_tipo: TipoAtor
    motivo: str | None = None
    ocorrido_em: datetime

    @classmethod
    def de(cls, mudanca: MudancaDeStatus) -> "MudancaDeStatusResponse":
        return cls(
            status_anterior=mudanca.status_anterior,
            status_novo=mudanca.status_novo,
            ator_tipo=mudanca.ator_tipo,
            motivo=mudanca.motivo,
            ocorrido_em=mudanca.ocorrido_em,
        )


def resposta_de_pedido_criado(pedido: PedidoDetalhe) -> RespostaGravada:
    """Corpo do 201, gravado com a Idempotency-Key para ser reproduzido byte a byte nas repetições."""
    return RespostaGravada(status_code=STATUS_CRIADO, corpo=PedidoResponse.de(pedido).model_dump(mode="json"))
