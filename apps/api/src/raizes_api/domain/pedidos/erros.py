from raizes_api.domain.compartilhado.erros import ErroDominio


class CanalIncompativel(ErroDominio):
    codigo = "CANAL_INCOMPATIVEL"
    mensagem_padrao = "O canal do pedido não é permitido para quem está autenticado."


class IdentificacaoClienteNaoPermitida(ErroDominio):
    codigo = "VALIDACAO"
    mensagem_padrao = "Um ou mais campos são inválidos."


class EstoqueInsuficiente(ErroDominio):
    codigo = "ESTOQUE_INSUFICIENTE"
    mensagem_padrao = "Não há quantidade suficiente para um ou mais itens."


class PedidoNaoEncontrado(ErroDominio):
    codigo = "PEDIDO_NAO_ENCONTRADO"
    mensagem_padrao = "O pedido não existe."


class TransicaoStatusInvalida(ErroDominio):
    codigo = "TRANSICAO_STATUS_INVALIDA"
    mensagem_padrao = "A mudança de status pedida não existe para o status atual do pedido."
