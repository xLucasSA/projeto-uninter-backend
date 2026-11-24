from raizes_api.domain.compartilhado.erros import ErroDominio


class PagamentoNaoPermitido(ErroDominio):
    codigo = "PAGAMENTO_NAO_PERMITIDO"
    mensagem_padrao = "O pedido não aguarda pagamento ou já tem um pagamento em andamento ou aprovado."


class PagamentoEmAndamento(ErroDominio):
    codigo = "PAGAMENTO_EM_ANDAMENTO"
    mensagem_padrao = "Há um pagamento em andamento para este pedido; aguarde o resultado antes de cancelar."
