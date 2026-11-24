from raizes_api.domain.compartilhado.atores import AtorAutenticado, Perfil, TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.erros import DetalheErro, PermissaoNegada
from raizes_api.domain.pedidos.erros import CanalIncompativel, IdentificacaoClienteNaoPermitida

CANAIS_DO_CLIENTE = frozenset({CanalPedido.APP, CanalPedido.WEB, CanalPedido.PICKUP})
CANAIS_DO_DISPOSITIVO = frozenset({CanalPedido.TOTEM})
CANAIS_DO_ATENDENTE = frozenset({CanalPedido.BALCAO})


def validar_criacao_pelo_ator(
    ator: AtorAutenticado, canal: CanalPedido, *, informou_identificacao_cliente: bool
) -> None:
    """O canal não é só declarado: ele precisa ser compatível com quem está autenticado (guideline 03).

    O escopo de unidade é verificado à parte, com auditoria do acesso negado.
    """
    if canal not in canais_permitidos(ator):
        raise CanalIncompativel()
    if ator.tipo is TipoAtor.CLIENTE and informou_identificacao_cliente:
        raise IdentificacaoClienteNaoPermitida(
            detalhes=[
                DetalheErro(
                    "identificacaoCliente", "Não permitido em pedidos do cliente: o cliente vem do token."
                )
            ]
        )


def canais_permitidos(ator: AtorAutenticado) -> frozenset[CanalPedido]:
    if ator.tipo is TipoAtor.CLIENTE:
        return CANAIS_DO_CLIENTE
    if ator.tipo is TipoAtor.DISPOSITIVO:
        return CANAIS_DO_DISPOSITIVO
    if Perfil.ATENDENTE in ator.perfis:
        return CANAIS_DO_ATENDENTE
    raise PermissaoNegada()
