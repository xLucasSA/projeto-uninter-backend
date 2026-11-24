import asyncio
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# O Django grava "argon2" + o hash do argon2-cffi ("argon2$argon2id$v=19$...").
# Sem esse prefixo, o formato é o mesmo que o argon2-cffi verifica.
PREFIXO_DJANGO = "argon2"


class HasherSenhaArgon2:
    """Argon2id via argon2-cffi. O cálculo roda numa thread para não bloquear o event loop."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        self._hash_ficticio = self._hasher.hash(secrets.token_urlsafe())

    async def gerar_hash(self, senha: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, senha)

    async def confere(self, hash_armazenado: str | None, senha: str) -> bool:
        if hash_armazenado is None:
            await asyncio.to_thread(self._verificar, self._hash_ficticio, senha)
            return False
        return await asyncio.to_thread(self._verificar, _sem_prefixo_do_django(hash_armazenado), senha)

    def _verificar(self, hash_argon2: str, senha: str) -> bool:
        try:
            return self._hasher.verify(hash_argon2, senha)
        except (VerificationError, InvalidHashError):
            return False


def _sem_prefixo_do_django(hash_armazenado: str) -> str:
    if hash_armazenado.startswith(f"{PREFIXO_DJANGO}$"):
        return hash_armazenado.removeprefix(PREFIXO_DJANGO)
    return hash_armazenado
