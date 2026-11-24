"""Máquina de estados do pedido (guideline 03): quais transições existem e quem pode fazê-las."""

from collections.abc import Mapping
from enum import StrEnum

from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor
from raizes_api.domain.compartilhado.erros import PermissaoNegada
from raizes_api.domain.pedidos.erros import TransicaoStatusInvalida


class StatusPedido(StrEnum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    CANCELADO = "CANCELADO"


STATUS_TERMINAIS = frozenset({StatusPedido.ENTREGUE, StatusPedido.PAGAMENTO_RECUSADO, StatusPedido.CANCELADO})
# Os únicos status que o funcionário informa no PATCH; os demais vêm do pagamento ou do cancelamento.
STATUS_DA_OPERACAO = frozenset({StatusPedido.EM_PREPARO, StatusPedido.PRONTO, StatusPedido.ENTREGUE})

_SO_O_SISTEMA: frozenset[Perfil] = frozenset()
_GERENCIA = frozenset({Perfil.GERENTE, Perfil.MATRIZ})

# Transição → perfis que podem executá-la. Conjunto vazio: só o SISTEMA (webhook do gateway).
# A posse do pedido (cliente dono, totem que criou) e o escopo de unidade são checados antes, no caso de uso.
PERFIS_POR_TRANSICAO: Mapping[tuple[StatusPedido, StatusPedido], frozenset[Perfil]] = {
    (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PAGO): _SO_O_SISTEMA,
    (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PAGAMENTO_RECUSADO): _SO_O_SISTEMA,
    (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO): frozenset(
        {Perfil.CLIENTE, Perfil.DISPOSITIVO, Perfil.ATENDENTE}
    )
    | _GERENCIA,
    (StatusPedido.PAGO, StatusPedido.CANCELADO): _GERENCIA,
    (StatusPedido.PAGO, StatusPedido.EM_PREPARO): frozenset({Perfil.COZINHA}) | _GERENCIA,
    (StatusPedido.EM_PREPARO, StatusPedido.PRONTO): frozenset({Perfil.COZINHA}) | _GERENCIA,
    (StatusPedido.PRONTO, StatusPedido.ENTREGUE): frozenset({Perfil.ATENDENTE}) | _GERENCIA,
}


def exigir_transicao(atual: StatusPedido, novo: StatusPedido, ator: AtorAutenticado) -> None:
    """Transição inexistente → 409; existente, mas não permitida a quem pede → 403 (nessa ordem)."""
    perfis = PERFIS_POR_TRANSICAO.get((atual, novo))
    if perfis is None:
        raise TransicaoStatusInvalida(f"O pedido não pode passar de {atual} para {novo}.")
    permitida = ator.tipo is TipoAtor.SISTEMA if not perfis else ator.possui_algum_perfil(perfis)
    if not permitida:
        raise PermissaoNegada()
