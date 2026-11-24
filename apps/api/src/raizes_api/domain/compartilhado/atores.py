from dataclasses import dataclass, field
from enum import StrEnum


class TipoAtor(StrEnum):
    CLIENTE = "CLIENTE"
    FUNCIONARIO = "FUNCIONARIO"
    DISPOSITIVO = "DISPOSITIVO"
    SISTEMA = "SISTEMA"


class Perfil(StrEnum):
    CLIENTE = "CLIENTE"
    DISPOSITIVO = "DISPOSITIVO"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    ESTOQUISTA = "ESTOQUISTA"
    GERENTE = "GERENTE"
    MATRIZ = "MATRIZ"


@dataclass(frozen=True, slots=True)
class AtorAutenticado:
    """Quem faz a requisição, como declarado no access token."""

    tipo: TipoAtor
    id: str
    perfis: frozenset[Perfil]
    unidades: frozenset[int] = field(default_factory=frozenset)

    def possui_algum_perfil(self, perfis: frozenset[Perfil]) -> bool:
        return not self.perfis.isdisjoint(perfis)
