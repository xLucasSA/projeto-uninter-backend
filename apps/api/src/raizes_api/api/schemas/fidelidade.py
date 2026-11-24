import uuid
from datetime import datetime

from pydantic import Field

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.application.ports.leitura import LancamentoResumo
from raizes_api.domain.fidelidade.lancamento import PONTOS_POR_REAL, TipoLancamento


class SaldoResponse(SchemaBase):
    saldo: int = Field(description="Soma dos lançamentos (créditos menos estornos).", examples=[129])
    pontos_por_real: int = Field(default=PONTOS_POR_REAL, examples=[PONTOS_POR_REAL])


class LancamentoResponse(SchemaBase):
    pedido_id: uuid.UUID
    tipo: TipoLancamento
    pontos: int = Field(description="Negativo no estorno.", examples=[129])
    criado_em: datetime

    @classmethod
    def de(cls, lancamento: LancamentoResumo) -> "LancamentoResponse":
        return cls(
            pedido_id=lancamento.pedido_id,
            tipo=lancamento.tipo,
            pontos=lancamento.pontos,
            criado_em=lancamento.criado_em,
        )
