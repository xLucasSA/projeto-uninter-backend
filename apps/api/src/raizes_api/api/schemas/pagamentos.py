import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.api.schemas.tipos import DinheiroJson
from raizes_api.application.ports.idempotencia import RespostaGravada
from raizes_api.application.ports.leitura import PagamentoResumo
from raizes_api.domain.pagamentos.pagamento import (
    FormaPagamento,
    Pagamento,
    ResultadoDoGateway,
    StatusPagamento,
)

STATUS_ACEITO = 202
FORMATO_TOKEN_PAGAMENTO = r"^tok_[a-z_]+$"  # noqa: S105 (é o formato do token, não um segredo)
TAMANHO_MAXIMO_MOTIVO_RECUSA = 60
TIPO_POR_RESULTADO = {
    ResultadoDoGateway.APROVADO: "pagamento.aprovado",
    ResultadoDoGateway.RECUSADO: "pagamento.recusado",
}


class SolicitarPagamentoRequest(SchemaBase):
    """Sem dados de cartão: só o token gerado pelo SDK do provedor (fora do escopo de PCI DSS)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"formaPagamento": "MOCK", "tokenPagamento": "tok_aprovado"}]}
    )

    forma_pagamento: Literal["MOCK"] = "MOCK"
    token_pagamento: str = Field(
        pattern=FORMATO_TOKEN_PAGAMENTO,
        max_length=40,
        description=(
            "Cenários do gateway simulado: `tok_aprovado`, `tok_recusado`, `tok_timeout`, "
            "`tok_webhook_duplicado`; outro `tok_*` é recusado como token inválido."
        ),
    )


class PagamentoAceitoResponse(SchemaBase):
    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    status: StatusPagamento = Field(examples=["PENDENTE"])
    valor: DinheiroJson = Field(examples=[29.80])
    solicitado_em: datetime

    @classmethod
    def de(cls, pagamento: Pagamento) -> "PagamentoAceitoResponse":
        return cls(
            pagamento_id=pagamento.id,
            pedido_id=pagamento.pedido_id,
            status=pagamento.status,
            valor=pagamento.valor.valor,
            solicitado_em=pagamento.solicitado_em,
        )


class PagamentoResponse(SchemaBase):
    pagamento_id: uuid.UUID
    status: StatusPagamento
    forma_pagamento: FormaPagamento
    valor: DinheiroJson = Field(examples=[29.80])
    motivo_recusa: str | None = Field(default=None, examples=["SALDO_INSUFICIENTE"])
    tentativas: int = Field(description="Chamadas feitas ao gateway nesta solicitação.", examples=[1])
    solicitado_em: datetime
    concluido_em: datetime | None = None

    @classmethod
    def de(cls, pagamento: PagamentoResumo) -> "PagamentoResponse":
        return cls(
            pagamento_id=pagamento.id,
            status=pagamento.status,
            forma_pagamento=pagamento.forma,
            valor=pagamento.valor,
            motivo_recusa=pagamento.motivo_recusa,
            tentativas=pagamento.tentativas,
            solicitado_em=pagamento.solicitado_em,
            concluido_em=pagamento.concluido_em,
        )


class WebhookPagamentoRequest(SchemaBase):
    """Notificação do gateway. A assinatura do corpo bruto é conferida antes desta validação."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "eventId": "e1d2c3b4-5a69-4788-9abc-def012345678",
                    "tipo": "pagamento.aprovado",
                    "transacaoId": "trx_7f3a9c",
                    "pagamentoId": "9a1e2b3c-4d5e-4f60-8a7b-9c0d1e2f3a4b",
                    "pedidoId": "0f8b6c1e-2d4a-4b8f-9c3e-6a7b8c9d0e1f",
                    "status": "APROVADO",
                    "valor": 29.80,
                    "motivo": None,
                    "ocorridoEm": "2026-11-10T12:00:07Z",
                }
            ]
        }
    )

    event_id: uuid.UUID
    tipo: Literal["pagamento.aprovado", "pagamento.recusado"]
    transacao_id: str = Field(min_length=1, max_length=64)
    pagamento_id: uuid.UUID
    pedido_id: uuid.UUID
    status: ResultadoDoGateway
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    motivo: str | None = Field(default=None, max_length=TAMANHO_MAXIMO_MOTIVO_RECUSA)
    ocorrido_em: AwareDatetime

    @model_validator(mode="after")
    def _tipo_coerente_com_status(self) -> Self:
        if TIPO_POR_RESULTADO[self.status] != self.tipo:
            raise ValueError(f"`tipo` {self.tipo} não corresponde ao status {self.status}.")
        return self


class WebhookResponse(SchemaBase):
    status: Literal["PROCESSADO", "IGNORADO"] = Field(
        description="IGNORADO: evento repetido, pagamento já final ou sem correspondência (nada muda)."
    )


def resposta_de_pagamento_aceito(pagamento: Pagamento) -> RespostaGravada:
    """Corpo do 202, gravado com a Idempotency-Key para ser reproduzido nas repetições."""
    return RespostaGravada(
        status_code=STATUS_ACEITO, corpo=PagamentoAceitoResponse.de(pagamento).model_dump(mode="json")
    )
