from datetime import timedelta
from typing import Protocol

from raizes_api.domain.compartilhado.atores import AtorAutenticado


class HasherSenha(Protocol):
    async def gerar_hash(self, senha: str) -> str: ...

    async def confere(self, hash_armazenado: str | None, senha: str) -> bool:
        """Verifica a senha contra o hash (formato do argon2-cffi ou do Django).

        Sem hash (conta inexistente ou anonimizada), compara com um hash fictício e retorna False:
        o tempo de resposta não revela se a conta existe.
        """
        ...


class EmissorTokens(Protocol):
    def emitir(self, ator: AtorAutenticado, validade: timedelta) -> str: ...

    def validar(self, token: str) -> AtorAutenticado:
        """Confere assinatura, expiração, emissor, audiência e claims; senão lança `TokenInvalido`."""
        ...


class VerificadorAssinaturaWebhook(Protocol):
    def verificar(self, corpo: bytes, timestamp: str | None, assinatura: str | None) -> None:
        """Confere o HMAC do corpo bruto e a janela do timestamp; senão lança `AssinaturaWebhookInvalida`."""
        ...
