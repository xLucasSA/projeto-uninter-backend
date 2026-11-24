import uuid
from typing import Protocol

from raizes_api.domain.clientes.cliente import Cliente, Consentimento
from raizes_api.domain.compartilhado.contato import Telefone


class RepositorioClientes(Protocol):
    async def obter(self, cliente_id: uuid.UUID) -> Cliente | None: ...

    async def obter_para_atualizacao(self, cliente_id: uuid.UUID) -> Cliente | None:
        """Bloqueia o cliente até o fim da transação, serializando alterações concorrentes."""
        ...

    async def obter_por_email(self, email: str) -> Cliente | None: ...

    async def obter_por_telefone(self, telefone: Telefone) -> Cliente | None: ...

    async def adicionar(self, cliente: Cliente) -> None:
        """Grava o cliente e seus consentimentos.

        Lança `EmailJaCadastrado` ou `TelefoneJaCadastrado` se a unicidade for violada.
        """
        ...

    async def adicionar_consentimento(self, cliente_id: uuid.UUID, consentimento: Consentimento) -> None: ...

    async def registrar_revogacao(self, consentimento: Consentimento) -> None: ...
