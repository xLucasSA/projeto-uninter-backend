from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EventoIntegracao:
    """Fato de negócio publicado pela outbox. `dados` nunca contém dado pessoal (guideline 07)."""

    tipo: str
    tipo_agregado: str
    agregado_id: str
    unidade_id: int | None = None
    dados: Mapping[str, object] = field(default_factory=dict)


class GravadorOutbox(Protocol):
    """Grava o evento na transação da Unit of Work (outbox pattern)."""

    async def publicar(self, evento: EventoIntegracao) -> None: ...
