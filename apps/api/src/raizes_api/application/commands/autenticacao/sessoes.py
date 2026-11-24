import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from raizes_api.application.ports.autenticacao import RepositorioRefreshTokens
from raizes_api.application.ports.relogio import Relogio
from raizes_api.application.ports.seguranca import EmissorTokens
from raizes_api.domain.autenticacao.refresh_token import RefreshToken
from raizes_api.domain.compartilhado.atores import AtorAutenticado

BYTES_ALEATORIOS_REFRESH = 32


@dataclass(frozen=True, slots=True)
class ValidadesSessao:
    acesso: timedelta
    refresh: timedelta
    dispositivo: timedelta


@dataclass(frozen=True, slots=True)
class AcessoEmitido:
    token_acesso: str
    expira_em_segundos: int


@dataclass(frozen=True, slots=True)
class SessaoEmitida:
    token_acesso: str
    expira_em_segundos: int
    refresh_token: str


def hash_do_refresh_token(valor: str) -> str:
    # 256 bits aleatórios dispensam hash lento (não há dicionário a atacar);
    # o SHA-256 permite buscar o token por igualdade.
    return hashlib.sha256(valor.encode()).hexdigest()


class EmissaoDeSessao:
    """Emite access tokens e mantém as famílias de refresh tokens rotativos (ADR-006)."""

    def __init__(self, emissor: EmissorTokens, relogio: Relogio, validades: ValidadesSessao) -> None:
        self._emissor = emissor
        self._relogio = relogio
        self._validades = validades

    async def abrir(self, refresh_tokens: RepositorioRefreshTokens, ator: AtorAutenticado) -> SessaoEmitida:
        sessao, _ = await self._emitir(refresh_tokens, ator, familia_id=uuid.uuid4())
        return sessao

    async def rotacionar(
        self, refresh_tokens: RepositorioRefreshTokens, ator: AtorAutenticado, anterior: RefreshToken
    ) -> SessaoEmitida:
        sessao, novo = await self._emitir(refresh_tokens, ator, familia_id=anterior.familia_id)
        await refresh_tokens.marcar_substituido(anterior.id, novo.id)
        return sessao

    def acesso_de_dispositivo(self, ator: AtorAutenticado) -> AcessoEmitido:
        validade = self._validades.dispositivo
        return AcessoEmitido(
            token_acesso=self._emissor.emitir(ator, validade),
            expira_em_segundos=int(validade.total_seconds()),
        )

    async def _emitir(
        self, refresh_tokens: RepositorioRefreshTokens, ator: AtorAutenticado, *, familia_id: uuid.UUID
    ) -> tuple[SessaoEmitida, RefreshToken]:
        valor_refresh = secrets.token_urlsafe(BYTES_ALEATORIOS_REFRESH)
        novo = RefreshToken(
            id=uuid.uuid4(),
            sujeito_tipo=ator.tipo,
            sujeito_id=ator.id,
            familia_id=familia_id,
            expira_em=self._relogio.agora() + self._validades.refresh,
        )
        await refresh_tokens.adicionar(novo, hash_do_refresh_token(valor_refresh))
        sessao = SessaoEmitida(
            token_acesso=self._emissor.emitir(ator, self._validades.acesso),
            expira_em_segundos=int(self._validades.acesso.total_seconds()),
            refresh_token=valor_refresh,
        )
        return sessao, novo
