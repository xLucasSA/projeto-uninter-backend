import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from raizes_api.domain.autenticacao.credenciais import Dispositivo, Funcionario
from raizes_api.domain.autenticacao.refresh_token import RefreshToken
from raizes_api.domain.compartilhado.atores import TipoAtor
from raizes_api.infrastructure.db.modelos import (
    DispositivoModel,
    FuncionarioModel,
    RefreshTokenModel,
    auth_group,
    funcionarios_groups,
    funcionarios_unidades,
)


class RepositorioFuncionariosSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def obter(self, funcionario_id: int) -> Funcionario | None:
        return await self._carregar(FuncionarioModel.id == funcionario_id)

    async def obter_por_email(self, email: str) -> Funcionario | None:
        return await self._carregar(FuncionarioModel.email == email)

    async def _carregar(self, criterio: ColumnElement[bool]) -> Funcionario | None:
        modelo = (await self._sessao.execute(select(FuncionarioModel).where(criterio))).scalar_one_or_none()
        if modelo is None:
            return None
        grupos = await self._sessao.scalars(
            select(auth_group.c.name)
            .join(funcionarios_groups, funcionarios_groups.c.group_id == auth_group.c.id)
            .where(funcionarios_groups.c.funcionario_id == modelo.id)
        )
        unidades = await self._sessao.scalars(
            select(funcionarios_unidades.c.unidade_id).where(
                funcionarios_unidades.c.funcionario_id == modelo.id
            )
        )
        return Funcionario(
            id=modelo.id,
            nome=modelo.nome,
            senha_hash=modelo.password,
            esta_ativo=modelo.is_active,
            eh_superusuario=modelo.is_superuser,
            grupos=frozenset(grupos),
            unidades=frozenset(unidades),
        )


class RepositorioDispositivosSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def obter_por_client_id(self, client_id: str) -> Dispositivo | None:
        modelo = (
            await self._sessao.execute(
                select(DispositivoModel).where(DispositivoModel.client_id == client_id)
            )
        ).scalar_one_or_none()
        if modelo is None:
            return None
        return Dispositivo(
            id=modelo.id,
            nome=modelo.nome,
            unidade_id=modelo.unidade_id,
            segredo_hash=modelo.secret_hash,
            esta_ativo=modelo.ativo,
        )

    async def registrar_uso(self, dispositivo_id: int, agora: datetime) -> None:
        await self._sessao.execute(
            update(DispositivoModel)
            .where(DispositivoModel.id == dispositivo_id)
            .values(ultimo_uso_em=agora)
            .execution_options(synchronize_session=False)
        )


class RepositorioRefreshTokensSql:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def adicionar(self, token: RefreshToken, token_hash: str) -> None:
        self._sessao.add(
            RefreshTokenModel(
                id=token.id,
                sujeito_tipo=token.sujeito_tipo.value,
                sujeito_id=token.sujeito_id,
                token_hash=token_hash,
                familia_id=token.familia_id,
                expira_em=token.expira_em,
            )
        )
        await self._sessao.flush()

    async def obter_para_atualizacao(self, token_hash: str) -> RefreshToken | None:
        modelo = (
            await self._sessao.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash).with_for_update()
            )
        ).scalar_one_or_none()
        if modelo is None:
            return None
        return RefreshToken(
            id=modelo.id,
            sujeito_tipo=TipoAtor(modelo.sujeito_tipo),
            sujeito_id=modelo.sujeito_id,
            familia_id=modelo.familia_id,
            expira_em=modelo.expira_em,
            substituido_por=modelo.substituido_por,
            revogado_em=modelo.revogado_em,
        )

    async def marcar_substituido(self, token_id: uuid.UUID, substituto_id: uuid.UUID) -> None:
        await self._sessao.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(substituido_por=substituto_id)
            .execution_options(synchronize_session=False)
        )

    async def revogar_familia(self, familia_id: uuid.UUID, agora: datetime) -> None:
        await self._sessao.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.familia_id == familia_id, RefreshTokenModel.revogado_em.is_(None))
            .values(revogado_em=agora)
            .execution_options(synchronize_session=False)
        )
