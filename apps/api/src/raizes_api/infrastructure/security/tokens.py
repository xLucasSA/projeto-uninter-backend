import uuid
from datetime import timedelta
from typing import Any

import jwt

from raizes_api.application.erros import TokenInvalido
from raizes_api.application.ports.relogio import Relogio
from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor

EMISSOR = "raizes-api"
AUDIENCIA = "raizes"
ALGORITMO = "HS256"
TOLERANCIA_RELOGIO = timedelta(seconds=10)
CLAIMS_OBRIGATORIAS = ["iss", "aud", "sub", "iat", "exp", "jti", "tipo", "perfis", "unidades"]
TIPOS_COM_TOKEN = frozenset({TipoAtor.CLIENTE, TipoAtor.FUNCIONARIO, TipoAtor.DISPOSITIVO})


class EmissorTokensJwt:
    def __init__(self, segredo: str, relogio: Relogio) -> None:
        self._segredo = segredo
        self._relogio = relogio

    def emitir(self, ator: AtorAutenticado, validade: timedelta) -> str:
        agora = self._relogio.agora()
        claims: dict[str, Any] = {
            "iss": EMISSOR,
            "aud": AUDIENCIA,
            "sub": ator.id,
            "tipo": ator.tipo.value,
            "perfis": sorted(perfil.value for perfil in ator.perfis),
            "unidades": sorted(ator.unidades),
            "iat": agora,
            "exp": agora + validade,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self._segredo, algorithm=ALGORITMO)

    def validar(self, token: str) -> AtorAutenticado:
        try:
            claims = jwt.decode(
                token,
                self._segredo,
                algorithms=[ALGORITMO],
                audience=AUDIENCIA,
                issuer=EMISSOR,
                leeway=TOLERANCIA_RELOGIO,
                options={"require": CLAIMS_OBRIGATORIAS},
            )
            return _ator_das_claims(claims)
        except (jwt.InvalidTokenError, ValueError, TypeError) as erro:
            raise TokenInvalido() from erro


def _ator_das_claims(claims: dict[str, Any]) -> AtorAutenticado:
    tipo = TipoAtor(claims["tipo"])
    if tipo not in TIPOS_COM_TOKEN or not isinstance(claims["perfis"], list):
        raise ValueError("Claims de tipo ou perfis inválidas.")
    return AtorAutenticado(
        tipo=tipo,
        id=str(claims["sub"]),
        perfis=frozenset(Perfil(perfil) for perfil in claims["perfis"]),
        unidades=frozenset(int(unidade) for unidade in claims["unidades"]),
    )
