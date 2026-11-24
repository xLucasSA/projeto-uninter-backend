import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from payment_mock.cenarios import StatusTransacao
from payment_mock.transacoes import Transacao

Valor = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class EsquemaBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True, serialize_by_alias=True
    )


class SolicitacaoTransacao(EsquemaBase):
    """Não há campo de URL de retorno: o webhook vai só para a URL configurada no mock (evita SSRF)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "pagamentoId": "9a1e2b3c-4d5e-4f60-8a7b-1c2d3e4f5a6b",
                    "pedidoId": "0f8b6c1e-2d4a-4b8f-9c3e-6a7b8c9d0e1f",
                    "valor": 29.80,
                    "moeda": "BRL",
                    "tokenPagamento": "tok_aprovado",
                }
            ]
        }
    )

    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    moeda: Literal["BRL"] = "BRL"
    token_pagamento: str = Field(pattern=r"^tok_[a-z_]+$", max_length=60)


class TransacaoAceitaResponse(EsquemaBase):
    transacao_id: str = Field(examples=["trx_7f3a9c1e5b2d4a6f8e0c1b3d5f7a9c1e"])
    status: StatusTransacao


class TransacaoResponse(EsquemaBase):
    transacao_id: str
    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    status: StatusTransacao
    valor: Valor
    moeda: str
    motivo: str | None = None
    criada_em: datetime

    @classmethod
    def de(cls, transacao: Transacao) -> "TransacaoResponse":
        return cls(
            transacao_id=transacao.transacao_id,
            pagamento_id=transacao.pagamento_id,
            pedido_id=transacao.pedido_id,
            status=transacao.status,
            valor=transacao.valor,
            moeda=transacao.moeda,
            motivo=transacao.motivo,
            criada_em=transacao.criada_em,
        )
