import ipaddress
import uuid

from sqlalchemy import ScalarSelect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from raizes_api.application.correlacao import contexto_requisicao_atual
from raizes_api.application.ports.auditoria import RegistroAuditoria
from raizes_api.application.ports.relogio import Relogio
from raizes_api.infrastructure.db.modelos import AuditoriaModel, UnidadeModel
from raizes_api.infrastructure.serializacao import para_json


class GravadorAuditoriaSql:
    def __init__(self, sessao: AsyncSession, relogio: Relogio) -> None:
        self._sessao = sessao
        self._relogio = relogio

    async def registrar(self, registro: RegistroAuditoria) -> None:
        self._sessao.add(_para_modelo(registro, self._relogio))
        await self._sessao.flush()


class GravadorAuditoriaIndependenteSql:
    def __init__(self, fabrica_sessoes: async_sessionmaker[AsyncSession], relogio: Relogio) -> None:
        self._fabrica_sessoes = fabrica_sessoes
        self._relogio = relogio

    async def registrar(self, registro: RegistroAuditoria) -> None:
        async with self._fabrica_sessoes() as sessao, sessao.begin():
            sessao.add(_para_modelo(registro, self._relogio))


def _para_modelo(registro: RegistroAuditoria, relogio: Relogio) -> AuditoriaModel:
    contexto = contexto_requisicao_atual()
    return AuditoriaModel(
        id=uuid.uuid4(),
        ocorrido_em=relogio.agora(),
        ator_tipo=registro.ator_tipo.value,
        ator_id=registro.ator_id,
        acao=registro.acao.value,
        entidade=registro.entidade,
        entidade_id=registro.entidade_id,
        unidade_id=_unidade_se_existir(registro.unidade_id),
        dados=para_json(registro.dados),
        request_id=contexto.request_id if contexto else None,
        ip=_ip_valido(contexto.ip) if contexto else None,
    )


def _ip_valido(ip: str | None) -> str | None:
    if ip is None:
        return None
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return None


def _unidade_se_existir(unidade_id: int | None) -> ScalarSelect[int] | None:
    # Um acesso negado pode citar um ID de unidade que não existe; a FK para catalogo.unidades
    # exige NULL nesse caso, senão o registro da tentativa falharia.
    if unidade_id is None:
        return None
    return select(UnidadeModel.id).where(UnidadeModel.id == unidade_id).scalar_subquery()
