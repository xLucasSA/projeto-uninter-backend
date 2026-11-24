from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor


def unidades_do_escopo(ator: AtorAutenticado) -> frozenset[int] | None:
    """Unidades que o ator pode ver; None = todas.

    Cliente não tem escopo de unidade (pede em qualquer uma) e MATRIZ enxerga a rede inteira.
    """
    if ator.tipo is TipoAtor.CLIENTE or Perfil.MATRIZ in ator.perfis:
        return None
    return ator.unidades


def pode_acessar_unidade(ator: AtorAutenticado, unidade_id: int) -> bool:
    escopo = unidades_do_escopo(ator)
    return escopo is None or unidade_id in escopo
