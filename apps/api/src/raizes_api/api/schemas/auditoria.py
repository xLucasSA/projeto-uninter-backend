import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from raizes_api.api.schemas.base import SchemaBase
from raizes_api.application.ports.leitura import RegistroDaTrilha
from raizes_api.domain.compartilhado.atores import TipoAtor


class RegistroAuditoriaResponse(SchemaBase):
    """Sem IP e sem dados pessoais: `atorId` é o ID técnico (uuid do cliente, ID do funcionário)."""

    id: uuid.UUID
    ocorrido_em: datetime
    ator_tipo: TipoAtor
    ator_id: str = Field(examples=["GATEWAY_PAGAMENTO"])
    acao: str = Field(examples=["PAGAMENTO_APROVADO"])
    entidade: str = Field(examples=["PEDIDO"])
    entidade_id: str = Field(examples=["0f8b6c1e-2d4a-4b8f-9c3e-6a7b8c9d0e1f"])
    unidade_id: int | None = Field(default=None, examples=[1])
    dados: dict[str, Any] = Field(examples=[{"statusAnterior": "AGUARDANDO_PAGAMENTO", "statusNovo": "PAGO"}])
    request_id: str | None = None

    @classmethod
    def de(cls, registro: RegistroDaTrilha) -> "RegistroAuditoriaResponse":
        return cls(
            id=registro.id,
            ocorrido_em=registro.ocorrido_em,
            ator_tipo=registro.ator_tipo,
            ator_id=registro.ator_id,
            acao=registro.acao,
            entidade=registro.entidade,
            entidade_id=registro.entidade_id,
            unidade_id=registro.unidade_id,
            dados=registro.dados,
            request_id=registro.request_id,
        )
