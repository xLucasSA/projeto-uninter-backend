import uuid
from datetime import datetime
from typing import Protocol

from raizes_api.domain.autenticacao.credenciais import Dispositivo, Funcionario
from raizes_api.domain.autenticacao.refresh_token import RefreshToken


class RepositorioFuncionarios(Protocol):
    """Leitura de `catalogo.funcionarios`, que pertence ao back-office (Django)."""

    async def obter(self, funcionario_id: int) -> Funcionario | None: ...

    async def obter_por_email(self, email: str) -> Funcionario | None: ...


class RepositorioDispositivos(Protocol):
    async def obter_por_client_id(self, client_id: str) -> Dispositivo | None: ...

    async def registrar_uso(self, dispositivo_id: int, agora: datetime) -> None: ...


class RepositorioRefreshTokens(Protocol):
    async def adicionar(self, token: RefreshToken, token_hash: str) -> None: ...

    async def obter_para_atualizacao(self, token_hash: str) -> RefreshToken | None:
        """Bloqueia o token até o fim da transação: dois refreshes simultâneos não o rotacionam duas vezes."""
        ...

    async def marcar_substituido(self, token_id: uuid.UUID, substituto_id: uuid.UUID) -> None: ...

    async def revogar_familia(self, familia_id: uuid.UUID, agora: datetime) -> None: ...
