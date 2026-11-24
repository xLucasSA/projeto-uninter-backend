import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from raizes_api.domain.compartilhado.atores import TipoAtor


class SituacaoRefreshToken(StrEnum):
    VALIDO = "VALIDO"
    INVALIDO = "INVALIDO"
    REUTILIZADO = "REUTILIZADO"


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """Refresh opaco e rotativo. Tokens do mesmo login formam uma família, revogada inteira no reuso."""

    id: uuid.UUID
    sujeito_tipo: TipoAtor
    sujeito_id: str
    familia_id: uuid.UUID
    expira_em: datetime
    substituido_por: uuid.UUID | None = None
    revogado_em: datetime | None = None

    def situacao(self, agora: datetime) -> SituacaoRefreshToken:
        if self.revogado_em is not None or agora >= self.expira_em:
            return SituacaoRefreshToken.INVALIDO
        if self.substituido_por is not None:
            return SituacaoRefreshToken.REUTILIZADO
        return SituacaoRefreshToken.VALIDO

    def pertence_a(self, tipo: TipoAtor, sujeito_id: str) -> bool:
        return self.sujeito_tipo == tipo and self.sujeito_id == sujeito_id
