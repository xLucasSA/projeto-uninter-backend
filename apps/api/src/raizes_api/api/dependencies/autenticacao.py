from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from raizes_api.application.erros import TokenAusente
from raizes_api.application.ports.seguranca import EmissorTokens
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil
from raizes_api.domain.compartilhado.erros import PermissaoNegada

# auto_error=False: sem o header, quem responde é o erro padrão (TOKEN_AUSENTE), não o 403 do FastAPI.
esquema_bearer = HTTPBearer(auto_error=False, description="Access token obtido em /auth/*.")


def obter_emissor_tokens(request: Request) -> EmissorTokens:
    return cast(EmissorTokens, request.app.state.emissor_tokens)


async def obter_ator(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    emissor: EmissorTokens = Depends(obter_emissor_tokens),
) -> AtorAutenticado:
    if credenciais is None:
        raise TokenAusente()
    return emissor.validar(credenciais.credentials)


def exigir_perfis(*perfis: Perfil) -> Callable[..., Awaitable[AtorAutenticado]]:
    """Autorização por perfil (a rota pode ser chamada?). Escopo e dono do recurso ficam no caso de uso."""
    permitidos = frozenset(perfis)

    async def verificar_perfil(ator: AtorAutenticado = Depends(obter_ator)) -> AtorAutenticado:
        if not ator.possui_algum_perfil(permitidos):
            raise PermissaoNegada()
        return ator

    return verificar_perfil
