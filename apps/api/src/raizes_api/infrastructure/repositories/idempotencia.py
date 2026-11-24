import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, and_, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.application.ports.idempotencia import ChaveIdempotente, RegistroIdempotencia, RespostaGravada
from raizes_api.infrastructure.db.modelos import IdempotencyKeyModel

STATUS_PROCESSANDO = "PROCESSANDO"
STATUS_CONCLUIDA = "CONCLUIDA"
RESTRICAO_ESCOPO_DA_CHAVE = "idempotency_keys_escopo_unico"


class RepositorioIdempotenciaSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def reservar(
        self,
        chave: ChaveIdempotente,
        *,
        agora: datetime,
        expira_em: datetime,
        processando_abandonada_antes_de: datetime | None = None,
    ) -> RegistroIdempotencia | None:
        descartavel: ColumnElement[bool] = IdempotencyKeyModel.expira_em <= agora
        if processando_abandonada_antes_de is not None:
            descartavel = or_(
                descartavel,
                and_(
                    IdempotencyKeyModel.status == STATUS_PROCESSANDO,
                    IdempotencyKeyModel.criado_em <= processando_abandonada_antes_de,
                ),
            )
        await self._sessao.execute(delete(IdempotencyKeyModel).where(*_mesma_chave(chave), descartavel))
        # Se outra transação reservou a chave e ainda não confirmou, o ON CONFLICT espera
        # o commit (ou rollback) dela.
        # É isso que faz a requisição concorrente devolver o replay em vez de criar um segundo pedido.
        reservada = await self._sessao.scalar(
            insert(IdempotencyKeyModel)
            .values(
                id=uuid.uuid4(),
                sujeito=chave.sujeito,
                rota=chave.rota,
                chave=chave.chave,
                request_hash=chave.hash_requisicao,
                status=STATUS_PROCESSANDO,
                criado_em=agora,
                expira_em=expira_em,
            )
            .on_conflict_do_nothing(constraint=RESTRICAO_ESCOPO_DA_CHAVE)
            .returning(IdempotencyKeyModel.id)
        )
        if reservada is not None:
            return None
        existente = (
            await self._sessao.execute(select(IdempotencyKeyModel).where(*_mesma_chave(chave)))
        ).scalar_one()
        resposta = (
            RespostaGravada(status_code=existente.status_code, corpo=existente.resposta)
            if existente.status == STATUS_CONCLUIDA
            and existente.status_code is not None
            and existente.resposta is not None
            else None
        )
        return RegistroIdempotencia(hash_requisicao=existente.request_hash, resposta=resposta)

    async def concluir(self, chave: ChaveIdempotente, resposta: RespostaGravada) -> None:
        await self._sessao.execute(
            update(IdempotencyKeyModel)
            .where(*_mesma_chave(chave))
            .values(status=STATUS_CONCLUIDA, status_code=resposta.status_code, resposta=resposta.corpo)
            .execution_options(synchronize_session=False)
        )

    async def liberar(self, chave: ChaveIdempotente) -> None:
        await self._sessao.execute(delete(IdempotencyKeyModel).where(*_mesma_chave(chave)))


def _mesma_chave(chave: ChaveIdempotente) -> tuple[ColumnElement[bool], ...]:
    return (
        IdempotencyKeyModel.sujeito == chave.sujeito,
        IdempotencyKeyModel.rota == chave.rota,
        IdempotencyKeyModel.chave == chave.chave,
    )
