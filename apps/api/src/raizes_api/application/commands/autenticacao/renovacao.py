import uuid

from raizes_api.application.commands.autenticacao.sessoes import (
    EmissaoDeSessao,
    SessaoEmitida,
    hash_do_refresh_token,
)
from raizes_api.application.erros import RefreshTokenInvalido, RefreshTokenReutilizado
from raizes_api.application.ports.auditoria import AcaoAuditoria, RegistroAuditoria
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.unit_of_work import UnitOfWork
from raizes_api.domain.autenticacao.refresh_token import RefreshToken, SituacaoRefreshToken
from raizes_api.domain.compartilhado.atores import AtorAutenticado, TipoAtor

ENTIDADE_FAMILIA_REFRESH = "FAMILIA_REFRESH_TOKEN"


class RenovarSessao:
    def __init__(self, uow: UnitOfWork, sessoes: EmissaoDeSessao, relogio: Relogio) -> None:
        self._uow = uow
        self._sessoes = sessoes
        self._relogio = relogio

    async def executar(self, refresh_token: str) -> SessaoEmitida:
        agora = self._relogio.agora()
        async with self._uow as uow:
            armazenado = await uow.refresh_tokens.obter_para_atualizacao(hash_do_refresh_token(refresh_token))
            if armazenado is None:
                raise RefreshTokenInvalido()
            situacao = armazenado.situacao(agora)
            if situacao is SituacaoRefreshToken.INVALIDO:
                raise RefreshTokenInvalido()

            # O commit vem antes do raise: a revogação precisa persistir mesmo com a resposta 401.
            if situacao is SituacaoRefreshToken.REUTILIZADO:
                await uow.refresh_tokens.revogar_familia(armazenado.familia_id, agora)
                await uow.auditoria.registrar(_registro_de_reuso(armazenado))
                await uow.commit()
                raise RefreshTokenReutilizado()

            ator = await _ator_que_ainda_pode_autenticar(uow, armazenado)
            if ator is None:
                await uow.refresh_tokens.revogar_familia(armazenado.familia_id, agora)
                await uow.commit()
                raise RefreshTokenInvalido()

            sessao = await self._sessoes.rotacionar(uow.refresh_tokens, ator, armazenado)
            await uow.commit()
        return sessao


class EncerrarSessao:
    def __init__(self, uow: UnitOfWork, relogio: Relogio) -> None:
        self._uow = uow
        self._relogio = relogio

    async def executar(self, ator: AtorAutenticado, refresh_token: str) -> None:
        """Revoga a família do refresh informado. Token desconhecido ou de outro titular não tem efeito."""
        async with self._uow as uow:
            armazenado = await uow.refresh_tokens.obter_para_atualizacao(hash_do_refresh_token(refresh_token))
            if armazenado is None or not armazenado.pertence_a(ator.tipo, ator.id):
                return
            await uow.refresh_tokens.revogar_familia(armazenado.familia_id, self._relogio.agora())
            await uow.commit()


async def _ator_que_ainda_pode_autenticar(uow: UnitOfWork, token: RefreshToken) -> AtorAutenticado | None:
    """Relê o titular: desativação, anonimização e mudança de perfil valem já no próximo access token."""
    if token.sujeito_tipo is TipoAtor.CLIENTE:
        cliente = await uow.clientes.obter(uuid.UUID(token.sujeito_id))
        return cliente.como_ator() if cliente is not None and cliente.pode_autenticar() else None
    if token.sujeito_tipo is TipoAtor.FUNCIONARIO:
        funcionario = await uow.funcionarios.obter(int(token.sujeito_id))
        return funcionario.como_ator() if funcionario is not None and funcionario.esta_ativo else None
    return None


def _registro_de_reuso(token: RefreshToken) -> RegistroAuditoria:
    return RegistroAuditoria(
        ator_tipo=token.sujeito_tipo,
        ator_id=token.sujeito_id,
        acao=AcaoAuditoria.REFRESH_REUTILIZADO,
        entidade=ENTIDADE_FAMILIA_REFRESH,
        entidade_id=str(token.familia_id),
    )
