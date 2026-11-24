from dataclasses import dataclass

from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor

# Nomes dos Groups criados pela migration do back-office (contas/0002_grupos).
PERFIL_POR_GRUPO: dict[str, Perfil] = {
    "Atendente": Perfil.ATENDENTE,
    "Cozinha": Perfil.COZINHA,
    "Estoquista": Perfil.ESTOQUISTA,
    "Gerente": Perfil.GERENTE,
    "Matriz": Perfil.MATRIZ,
}


@dataclass(frozen=True, slots=True)
class Funcionario:
    """Usuário do back-office (Django) que opera pela API. Só leitura: o cadastro é do Django."""

    id: int
    nome: str
    senha_hash: str
    esta_ativo: bool
    eh_superusuario: bool
    grupos: frozenset[str]
    unidades: frozenset[int]

    def perfis(self) -> frozenset[Perfil]:
        perfis = {PERFIL_POR_GRUPO[grupo] for grupo in self.grupos if grupo in PERFIL_POR_GRUPO}
        if self.eh_superusuario:
            perfis.add(Perfil.MATRIZ)
        return frozenset(perfis)

    def como_ator(self) -> AtorAutenticado:
        return AtorAutenticado(
            tipo=TipoAtor.FUNCIONARIO, id=str(self.id), perfis=self.perfis(), unidades=self.unidades
        )


@dataclass(frozen=True, slots=True)
class Dispositivo:
    """Totem de autoatendimento, vinculado a uma única unidade."""

    id: int
    nome: str
    unidade_id: int
    segredo_hash: str
    esta_ativo: bool

    def como_ator(self) -> AtorAutenticado:
        return AtorAutenticado(
            tipo=TipoAtor.DISPOSITIVO,
            id=str(self.id),
            perfis=frozenset({Perfil.DISPOSITIVO}),
            unidades=frozenset({self.unidade_id}),
        )
