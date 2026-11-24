import uuid
from dataclasses import dataclass
from enum import StrEnum

from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor
from raizes_api.domain.compartilhado.escopo import pode_acessar_unidade

PERFIS_QUE_VEEM_PEDIDOS_DA_UNIDADE = frozenset(
    {Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE, Perfil.MATRIZ}
)


class AcessoAoPedido(StrEnum):
    PERMITIDO = "PERMITIDO"
    OCULTO = "OCULTO"
    PROIBIDO = "PROIBIDO"
    FORA_DO_ESCOPO = "FORA_DO_ESCOPO"


@dataclass(frozen=True, slots=True)
class VinculosDoPedido:
    unidade_id: int
    cliente_id: uuid.UUID | None
    criado_por_tipo: TipoAtor
    criado_por_id: str


def acesso_ao_pedido(ator: AtorAutenticado, vinculos: VinculosDoPedido) -> AcessoAoPedido:
    """Pedido de outro cliente ou de outro totem fica OCULTO (404: não revela que existe).

    Funcionário sabe que outras unidades existem: fora do escopo é 403, rastreável na auditoria.
    """
    if ator.tipo is TipoAtor.CLIENTE:
        return _permitido_se(vinculos.cliente_id is not None and str(vinculos.cliente_id) == ator.id)
    if ator.tipo is TipoAtor.DISPOSITIVO:
        criou = vinculos.criado_por_tipo is TipoAtor.DISPOSITIVO and vinculos.criado_por_id == ator.id
        return _permitido_se(criou)
    if not ator.possui_algum_perfil(PERFIS_QUE_VEEM_PEDIDOS_DA_UNIDADE):
        return AcessoAoPedido.PROIBIDO
    if not pode_acessar_unidade(ator, vinculos.unidade_id):
        return AcessoAoPedido.FORA_DO_ESCOPO
    return AcessoAoPedido.PERMITIDO


def _permitido_se(condicao: bool) -> AcessoAoPedido:
    return AcessoAoPedido.PERMITIDO if condicao else AcessoAoPedido.OCULTO
