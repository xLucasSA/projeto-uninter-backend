import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.application.ports.outbox import EventoIntegracao
from raizes_api.application.ports.relogio import Relogio
from raizes_api.infrastructure.db.modelos import OutboxEventoModel
from raizes_api.infrastructure.serializacao import para_json

VERSAO_ENVELOPE = 1


class GravadorOutboxSql:
    def __init__(self, sessao: AsyncSession, relogio: Relogio) -> None:
        self._sessao = sessao
        self._relogio = relogio

    async def publicar(self, evento: EventoIntegracao) -> None:
        event_id = uuid.uuid4()
        ocorrido_em = self._relogio.agora()
        envelope = {
            "versao": VERSAO_ENVELOPE,
            "eventId": str(event_id),
            "tipo": evento.tipo,
            "ocorridoEm": ocorrido_em.isoformat(),
            "unidadeId": evento.unidade_id,
            "dados": para_json(evento.dados),
        }
        self._sessao.add(
            OutboxEventoModel(
                id=event_id,
                aggregatetype=evento.tipo_agregado,
                aggregateid=evento.agregado_id,
                type=evento.tipo,
                payload=envelope,
                ocorrido_em=ocorrido_em,
            )
        )
        await self._sessao.flush()
